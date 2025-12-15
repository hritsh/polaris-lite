"""
RAG (Retrieval-Augmented Generation) module for the Constellation safety system.
Uses ChromaDB for vector storage and HuggingFace Transformers for embeddings.
Includes pre-populated medical knowledge base and supports PDF document upload.
"""

import os
import tempfile
from typing import Optional, List, Dict, Any
import hashlib
import logging
import threading

logger = logging.getLogger(__name__)

# ========== HuggingFace Transformers Embedding Model ==========
# Using all-MiniLM-L6-v2 via transformers directly (more explicit than sentence-transformers)
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Heavy deps are lazily imported/loaded to keep server startup fast.
_tokenizer = None
_model = None
_torch = None
_embedding_lock = threading.Lock()


def _ensure_embedding_model_loaded() -> None:
    global _tokenizer, _model, _torch
    if _tokenizer is not None and _model is not None and _torch is not None:
        return

    with _embedding_lock:
        if _tokenizer is not None and _model is not None and _torch is not None:
            return

        logger.info("Loading HuggingFace embedding model: %s", MODEL_NAME)

        import torch  # heavy
        from transformers import AutoTokenizer, AutoModel  # heavy

        _torch = torch
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        _model = AutoModel.from_pretrained(MODEL_NAME)
        _model.eval()

        logger.info("Embedding model loaded")


def _mean_pooling(model_output, attention_mask):
    """Mean pooling - take attention mask into account for correct averaging"""
    # Import is cached after first call; keeps module import fast.
    import torch

    token_embeddings = model_output[0]
    input_mask_expanded = attention_mask.unsqueeze(
        -1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)


def get_text_embedding(text: str) -> List[float]:
    """Generate embedding for text using HuggingFace Transformers."""
    _ensure_embedding_model_loaded()
    assert _tokenizer is not None and _model is not None and _torch is not None

    encoded_input = _tokenizer(
        text,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt",
    )

    with _torch.no_grad():
        model_output = _model(**encoded_input)

    embeddings = _mean_pooling(model_output, encoded_input["attention_mask"])
    embeddings = _torch.nn.functional.normalize(embeddings, p=2, dim=1)
    return embeddings[0].tolist()


# ========== RAG Toggle ==========
_rag_enabled = False  # Disabled by default for speed


def is_rag_enabled() -> bool:
    """Check if RAG mode is enabled"""
    return _rag_enabled


def set_rag_enabled(enabled: bool):
    """Enable or disable RAG mode"""
    global _rag_enabled
    _rag_enabled = enabled
    logger.info("RAG mode %s", "enabled" if enabled else "disabled")


# ========== ChromaDB Setup (Lazy) ==========
_vector_store_lock = threading.Lock()
_chroma_client = None
_collection = None


def _ensure_vector_store_initialized() -> None:
    """Initialize ChromaDB only when needed (keeps startup fast)."""
    global _chroma_client, _collection
    if _collection is not None:
        return

    with _vector_store_lock:
        if _collection is not None:
            return

        import chromadb
        from chromadb.config import Settings

        _chroma_client = chromadb.Client(
            Settings(
                anonymized_telemetry=False,
                is_persistent=False,
            )
        )

        _collection = _chroma_client.get_or_create_collection(
            name="medical_docs",
            metadata={"description": "Medical reference documents for nurse RAG"},
        )


def _get_collection():
    _ensure_vector_store_initialized()
    assert _collection is not None
    return _collection


# Track uploaded documents and pending (unindexed) documents.
uploaded_docs: Dict[str, Dict[str, Any]] = {}
_pending_documents: Dict[str, Dict[str, Any]] = {}


# ========== Pre-populated Medical Knowledge Base ==========
MEDICAL_KNOWLEDGE_BASE = [
    {
        "title": "OTC Pain Medication Dosing Guidelines",
        "content": """
Over-the-Counter Pain Medication Dosing Guidelines for Adults:

ACETAMINOPHEN (Tylenol):
- Standard dose: 325-650mg every 4-6 hours
- Maximum daily dose: 3,000mg (or 4,000mg under physician guidance)
- Warning: Liver toxicity risk with overdose or alcohol use
- Do NOT exceed 1,000mg per single dose

IBUPROFEN (Advil, Motrin):
- Standard dose: 200-400mg every 4-6 hours  
- Maximum daily dose: 1,200mg OTC (3,200mg prescription)
- Take with food to reduce stomach upset
- Avoid if history of stomach ulcers, kidney disease, or heart conditions
- Warning: Can increase bleeding risk

NAPROXEN (Aleve):
- Standard dose: 220mg every 8-12 hours
- Maximum daily dose: 660mg OTC
- Longer-lasting than ibuprofen
- Same warnings as ibuprofen (NSAIDs)

ASPIRIN:
- Standard dose: 325-650mg every 4-6 hours
- Maximum daily dose: 4,000mg
- Warning: NOT for children under 18 (Reye's syndrome risk)
- Increases bleeding risk significantly

IMPORTANT: Always consult a healthcare provider before combining pain medications.
"""
    },
    {
        "title": "Pediatric Medication Safety",
        "content": """
Pediatric Medication Dosing Safety Guidelines:

GENERAL PRINCIPLES:
- Always dose by WEIGHT (kg), not age alone
- Use calibrated measuring devices, not household spoons
- Never give adult formulations to children without physician guidance

ACETAMINOPHEN (Children's Tylenol):
- Dose: 10-15 mg/kg every 4-6 hours
- Maximum: 75 mg/kg/day (not to exceed 4,000mg)
- Available in infant drops, liquid, chewables

IBUPROFEN (Children's Motrin/Advil):
- Dose: 5-10 mg/kg every 6-8 hours
- NOT recommended under 6 months of age
- Give with food

MEDICATIONS TO AVOID IN CHILDREN:
- Aspirin: Risk of Reye's syndrome (under 18)
- Honey: Risk of botulism (under 12 months)
- Cough/cold medicines: Not recommended under 4 years
- Adult formulations: Concentration differences are dangerous

FEVER THRESHOLDS:
- Under 3 months: 100.4°F (38°C) = SEEK IMMEDIATE CARE
- 3-36 months: 102°F (38.9°C) = Contact pediatrician
- Over 3 years: 103°F (39.4°C) = Contact pediatrician

Always consult pediatrician before giving any medication to infants.
"""
    },
    {
        "title": "Common Drug Interactions",
        "content": """
Common Dangerous Drug Interactions to Avoid:

NSAIDs + BLOOD THINNERS (Warfarin, Aspirin):
- Significantly increased bleeding risk
- Can cause GI bleeding, bruising
- Includes: ibuprofen, naproxen, aspirin

NSAIDs + ACE INHIBITORS/ARBs (Blood Pressure Meds):
- Reduces blood pressure medication effectiveness
- Can worsen kidney function
- Common BP meds: lisinopril, losartan, enalapril

ACETAMINOPHEN + ALCOHOL:
- Increased risk of liver damage
- Avoid acetaminophen if drinking regularly
- Maximum 2,000mg/day if consuming alcohol

ANTIHISTAMINES + SEDATIVES/ALCOHOL:
- Excessive drowsiness and impairment
- Includes: Benadryl, Zyrtec, sleep aids
- Do not drive or operate machinery

GRAPEFRUIT + MANY MEDICATIONS:
- Can increase drug levels dangerously
- Affected drugs: statins, calcium channel blockers, some antibiotics
- Check medication labels

SSRI ANTIDEPRESSANTS + TRIPTANS (Migraine):
- Risk of serotonin syndrome
- Symptoms: agitation, rapid heart rate, high temperature
- Common SSRIs: Prozac, Zoloft, Lexapro

Always inform healthcare providers of ALL medications including supplements.
"""
    },
    {
        "title": "Emergency Warning Signs",
        "content": """
Medical Emergency Warning Signs - Seek Immediate Care:

CHEST PAIN:
- Pain radiating to arm, jaw, or back
- Accompanied by shortness of breath, sweating
- Feeling of pressure or squeezing
- ACTION: Call 911 immediately

STROKE SYMPTOMS (F.A.S.T.):
- Face drooping on one side
- Arm weakness or numbness
- Speech difficulty or confusion
- Time to call 911 - every minute matters

SEVERE ALLERGIC REACTION (Anaphylaxis):
- Difficulty breathing, throat swelling
- Rapid pulse, dizziness
- Widespread hives or swelling
- ACTION: Use EpiPen if available, call 911

HEAD INJURY:
- Loss of consciousness
- Persistent vomiting
- Worsening headache
- Confusion, slurred speech
- Unequal pupils

SIGNS OF INTERNAL BLEEDING:
- Vomiting blood or coffee-ground material
- Black, tarry stools
- Severe abdominal pain with rigidity
- Rapid pulse with pale skin

INFANT EMERGENCIES (Seek immediate care):
- Fever over 100.4°F under 3 months
- Difficulty breathing, blue lips
- Not responding or very limp
- Persistent vomiting, not keeping fluids down
"""
    },
    {
        "title": "Pregnancy and Medication Safety",
        "content": """
Medication Safety During Pregnancy and Breastfeeding:

GENERALLY CONSIDERED SAFE (with physician approval):
- Acetaminophen (Tylenol): First choice for pain/fever
- Certain antacids: Tums, Maalox
- Many prenatal vitamins with folic acid
- Certain antibiotics: Penicillin, Amoxicillin, Erythromycin

MEDICATIONS TO AVOID DURING PREGNANCY:
- Ibuprofen (Advil/Motrin): Especially in 3rd trimester
- Naproxen (Aleve): NSAID risks
- Aspirin: Bleeding risks (unless prescribed for specific conditions)
- Retinoids (Accutane): Severe birth defects
- Certain antibiotics: Tetracycline, Doxycycline
- Many herbal supplements: Not well studied

BREASTFEEDING CONSIDERATIONS:
- Most medications pass into breast milk
- Acetaminophen: Generally safe
- Ibuprofen: Generally safe in short-term use
- Avoid: Aspirin, certain antibiotics, sedatives

IMPORTANT WARNINGS:
- Always consult OB/GYN before taking ANY medication
- "Natural" does not mean safe during pregnancy
- Timing of medication matters (trimester-specific risks)
- Some medications require stopping before pregnancy

When in doubt, ask your healthcare provider before taking any medication.
"""
    }
]


def _init_builtin_doc_metadata() -> None:
    """Register built-in docs for listing without embedding them at import time."""
    for doc in MEDICAL_KNOWLEDGE_BASE:
        content = doc["content"]
        filename = f"{doc['title']}.txt"
        doc_id = hashlib.md5(content.encode()).hexdigest()[:12]

        if doc_id in uploaded_docs:
            continue

        uploaded_docs[doc_id] = {
            "filename": filename,
            "doc_type": "builtin",
            "chunks": 0,
            "chunk_ids": [],
            "is_builtin": True,
            "embedded": False,
        }


_builtin_index_lock = threading.Lock()
_builtin_indexed = False


def _ensure_builtin_docs_indexed() -> None:
    """Embed the built-in knowledge base into ChromaDB on-demand."""
    global _builtin_indexed
    if _builtin_indexed:
        return

    with _builtin_index_lock:
        if _builtin_indexed:
            return

        collection = _get_collection()

        for doc in MEDICAL_KNOWLEDGE_BASE:
            content = doc["content"]
            filename = f"{doc['title']}.txt"
            doc_id = hashlib.md5(content.encode()).hexdigest()[:12]

            # Chunk the document
            chunks = chunk_text(content)
            if not chunks:
                continue

            chunk_ids = []
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc_id}_{i}"
                chunk_ids.append(chunk_id)
                collection.add(
                    ids=[chunk_id],
                    documents=[chunk],
                    embeddings=[get_text_embedding(chunk)],
                    metadatas=[
                        {
                            "doc_id": doc_id,
                            "filename": filename,
                            "chunk_index": i,
                            "total_chunks": len(chunks),
                            "is_builtin": True,
                        }
                    ],
                )

            uploaded_docs[doc_id] = {
                "filename": filename,
                "doc_type": "builtin",
                "chunks": len(chunks),
                "chunk_ids": chunk_ids,
                "is_builtin": True,
                "embedded": True,
            }

        _builtin_indexed = True
        logger.info("Knowledge base indexed (%d docs)",
                    len(MEDICAL_KNOWLEDGE_BASE))


def _ensure_pending_docs_indexed() -> None:
    """Index any user-uploaded docs that were queued while RAG was disabled."""
    if not _pending_documents:
        return

    collection = _get_collection()

    # Copy keys to avoid mutating while iterating.
    pending_items = list(_pending_documents.items())
    for doc_id, info in pending_items:
        chunks = info["chunks"]
        filename = info["filename"]
        doc_type = info.get("doc_type", "pdf")

        chunk_ids = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_{i}"
            chunk_ids.append(chunk_id)
            collection.add(
                ids=[chunk_id],
                documents=[chunk],
                embeddings=[get_text_embedding(chunk)],
                metadatas=[
                    {
                        "doc_id": doc_id,
                        "filename": filename,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "doc_type": doc_type,
                    }
                ],
            )

        uploaded_docs[doc_id] = {
            "filename": filename,
            "doc_type": doc_type,
            "chunks": len(chunks),
            "chunk_ids": chunk_ids,
            "embedded": True,
        }

        del _pending_documents[doc_id]

    logger.info("Indexed %d pending documents", len(pending_items))


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text content from a PDF file"""
    try:
        from pypdf import PdfReader

        reader = PdfReader(pdf_path)
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        return "\n".join(text_parts)
    except Exception as e:
        logger.error(f"Error extracting PDF text: {e}")
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks for better retrieval.
    Uses paragraph-aware splitting when possible.
    """
    # Clean up text
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Try to split by paragraphs first
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

    chunks = []
    current_chunk = ""

    for para in paragraphs:
        # If paragraph is too long, split it
        if len(para) > chunk_size:
            # Split long paragraph into sentences
            sentences = para.replace('. ', '.\n').split('\n')
            for sentence in sentences:
                if len(current_chunk) + len(sentence) < chunk_size:
                    current_chunk += sentence + " "
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence + " "
        else:
            if len(current_chunk) + len(para) < chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"

    if current_chunk:
        chunks.append(current_chunk.strip())

    # Add overlap between chunks for context continuity
    if overlap > 0 and len(chunks) > 1:
        overlapped_chunks = []
        for i, chunk in enumerate(chunks):
            if i > 0:
                # Add end of previous chunk as prefix
                prev_end = chunks[i-1][-overlap:] if len(
                    chunks[i-1]) > overlap else chunks[i-1]
                chunk = prev_end + " ... " + chunk
            overlapped_chunks.append(chunk)
        return overlapped_chunks

    return chunks


def add_document(content: str, filename: str, doc_type: str = "pdf") -> dict:
    """
    Add a document to the RAG system.
    Chunks the document and stores embeddings in ChromaDB.
    """
    # Generate document ID from content hash
    doc_id = hashlib.md5(content.encode()).hexdigest()[:12]

    # Check if already uploaded
    if doc_id in uploaded_docs:
        return {
            "success": True,
            "message": "Document already exists",
            "doc_id": doc_id,
            "chunks": uploaded_docs[doc_id]["chunks"]
        }

    chunks = chunk_text(content)
    if not chunks:
        return {"success": False, "message": "No content could be extracted from document"}

    # If RAG is disabled, queue for indexing later so startup stays fast and uploads don't
    # force embedding model download.
    if not is_rag_enabled():
        _pending_documents[doc_id] = {
            "filename": filename,
            "doc_type": doc_type,
            "chunks": chunks,
        }
        uploaded_docs[doc_id] = {
            "filename": filename,
            "doc_type": doc_type,
            "chunks": len(chunks),
            "chunk_ids": [],
            "embedded": False,
        }
        logger.info(
            "Queued document '%s' for indexing when RAG is enabled", filename)
        return {
            "success": True,
            "message": "Document uploaded; indexing will run when RAG is enabled",
            "doc_id": doc_id,
            "chunks": len(chunks),
            "filename": filename,
        }

    collection = _get_collection()
    chunk_ids = []
    for i, chunk in enumerate(chunks):
        chunk_id = f"{doc_id}_{i}"
        chunk_ids.append(chunk_id)
        collection.add(
            ids=[chunk_id],
            documents=[chunk],
            embeddings=[get_text_embedding(chunk)],
            metadatas=[
                {
                    "doc_id": doc_id,
                    "filename": filename,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "doc_type": doc_type,
                }
            ],
        )

    uploaded_docs[doc_id] = {
        "filename": filename,
        "doc_type": doc_type,
        "chunks": len(chunks),
        "chunk_ids": chunk_ids,
        "embedded": True,
    }

    logger.info("Added document '%s' with %d chunks", filename, len(chunks))
    return {
        "success": True,
        "message": "Document uploaded successfully",
        "doc_id": doc_id,
        "chunks": len(chunks),
        "filename": filename,
    }


def add_pdf_document(pdf_path: str, filename: str) -> dict:
    """Add a PDF document to the RAG system"""
    text = extract_text_from_pdf(pdf_path)
    return add_document(text, filename, doc_type="pdf")


def get_relevant_context(query: str, n_results: int = 3) -> Optional[str]:
    """
    Retrieve relevant context from uploaded documents for a query.
    Returns concatenated relevant chunks or None if no documents uploaded.
    """
    if not is_rag_enabled():
        return None

    # First use of RAG: initialize and index built-ins and any queued docs.
    _ensure_builtin_docs_indexed()
    _ensure_pending_docs_indexed()

    collection = _get_collection()
    if collection.count() == 0:
        return None

    # Query the collection
    query_embedding = get_text_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, collection.count())
    )

    if not results["documents"] or not results["documents"][0]:
        return None

    # Combine relevant chunks with source info
    context_parts = []
    for i, (doc, metadata) in enumerate(zip(results["documents"][0], results["metadatas"][0])):
        source = metadata.get("filename", "Unknown")
        context_parts.append(f"[From {source}]:\n{doc}")

    return "\n\n---\n\n".join(context_parts)


def list_documents() -> List[dict]:
    """List all uploaded documents"""
    return [
        {
            "doc_id": doc_id,
            "filename": info["filename"],
            "chunks": info["chunks"],
            "doc_type": info["doc_type"],
            "is_builtin": info.get("is_builtin", False)
        }
        for doc_id, info in uploaded_docs.items()
    ]


def delete_document(doc_id: str) -> dict:
    """Delete a document from the RAG system (user documents only)"""
    if doc_id not in uploaded_docs:
        return {"success": False, "message": "Document not found"}

    # Don't allow deleting builtin documents
    if uploaded_docs[doc_id].get("is_builtin", False):
        return {"success": False, "message": "Cannot delete built-in knowledge base documents"}

    # Delete from vector store if indexed.
    chunk_ids = uploaded_docs[doc_id].get("chunk_ids") or []
    if chunk_ids:
        collection = _get_collection()
        collection.delete(ids=chunk_ids)

    # Delete any queued (unindexed) content.
    if doc_id in _pending_documents:
        del _pending_documents[doc_id]

    # Remove from tracking
    filename = uploaded_docs[doc_id]["filename"]
    del uploaded_docs[doc_id]

    logger.info(f"Deleted document '{filename}'")

    return {"success": True, "message": f"Document '{filename}' deleted"}


def clear_all_documents() -> dict:
    """Clear all user-uploaded documents (preserves builtin knowledge base)"""
    global uploaded_docs

    # Only delete user-uploaded documents
    user_doc_ids = [doc_id for doc_id, info in uploaded_docs.items(
    ) if not info.get("is_builtin", False)]

    for doc_id in user_doc_ids:
        chunk_ids = uploaded_docs[doc_id].get("chunk_ids") or []
        if chunk_ids:
            collection = _get_collection()
            collection.delete(ids=chunk_ids)

        if doc_id in _pending_documents:
            del _pending_documents[doc_id]

        del uploaded_docs[doc_id]

    return {"success": True, "message": f"Cleared {len(user_doc_ids)} user documents"}


def get_rag_stats() -> dict:
    """Get statistics about the RAG system"""
    docs = list_documents()
    builtin_count = sum(1 for d in docs if d.get("is_builtin", False))
    user_count = len(docs) - builtin_count

    total_chunks = 0
    if _collection is not None:
        try:
            total_chunks = _collection.count()
        except Exception:
            total_chunks = 0

    return {
        "total_documents": len(uploaded_docs),
        "builtin_documents": builtin_count,
        "user_documents": user_count,
        "total_chunks": total_chunks,
        "documents": docs
    }


# Register builtin docs for listing (no embeddings at import time)
_init_builtin_doc_metadata()
