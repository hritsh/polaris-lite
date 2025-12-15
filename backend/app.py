from prompts import get_active_auditors, AUDITOR_CONFIG
from rag import (
    add_pdf_document,
    add_document,
    list_documents,
    delete_document,
    clear_all_documents,
    get_rag_stats,
    is_rag_enabled,
    set_rag_enabled
)
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import asyncio
import json
import tempfile
import os
from config import FRONTEND_URL

# Fast original agents (default)
from agents import (
    get_nurse_draft as get_nurse_draft_fast,
    run_auditor as run_auditor_fast,
    get_corrected_response as get_corrected_response_fast
)

# LangChain agents with RAG support (optional, slower)
# Lazily imported when RAG is enabled to keep startup fast.
_langchain_funcs = None


def _get_langchain_funcs():
    global _langchain_funcs
    if _langchain_funcs is None:
        from langchain_agents import (
            get_nurse_draft_langchain,
            run_auditor_langchain,
            get_corrected_response_langchain,
        )
        _langchain_funcs = (
            get_nurse_draft_langchain,
            run_auditor_langchain,
            get_corrected_response_langchain,
        )
    return _langchain_funcs


app = Flask(__name__)

# cors setup - allow frontend to talk to us
CORS(
    app,
    origins=[FRONTEND_URL, "http://localhost:3000"],
    supports_credentials=True,
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"]
)


@app.route("/health", methods=["GET"])
def health():
    """health check endpoint for render"""
    rag_info = get_rag_stats()
    return jsonify({
        "status": "ok",
        "message": "constellation is running",
        "features": {
            "langchain": True,
            "rag_available": True,
            "rag_enabled": is_rag_enabled(),
            "documents_loaded": rag_info["total_documents"]
        }
    })


# ========== RAG Document Upload Endpoints ==========

@app.route("/documents/upload", methods=["POST"])
def upload_document():
    """
    Upload a PDF document for RAG.
    Supports file upload or raw text.
    """
    # Check if file upload
    if 'file' in request.files:
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        if not file.filename.lower().endswith('.pdf'):
            return jsonify({"error": "Only PDF files are supported"}), 400

        # Save to temp file and process
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                file.save(tmp.name)
                result = add_pdf_document(tmp.name, file.filename)
                os.unlink(tmp.name)  # Clean up

            return jsonify(result), 200 if result["success"] else 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Check if raw text
    data = request.get_json()
    if data and "text" in data:
        filename = data.get("filename", "text_document.txt")
        result = add_document(data["text"], filename, doc_type="text")
        return jsonify(result), 200 if result["success"] else 400

    return jsonify({"error": "No file or text provided"}), 400


@app.route("/documents", methods=["GET"])
def get_documents():
    """List all uploaded documents"""
    return jsonify(get_rag_stats())


@app.route("/documents/<doc_id>", methods=["DELETE"])
def remove_document(doc_id):
    """Delete a specific document"""
    result = delete_document(doc_id)
    return jsonify(result), 200 if result["success"] else 404


@app.route("/documents/clear", methods=["POST"])
def clear_documents():
    """Clear all uploaded documents"""
    result = clear_all_documents()
    return jsonify(result)


@app.route("/rag/toggle", methods=["POST"])
def toggle_rag():
    """Toggle RAG mode on/off"""
    data = request.get_json()
    enabled = data.get("enabled", False) if data else False
    set_rag_enabled(enabled)
    return jsonify({"rag_enabled": is_rag_enabled()})


@app.route("/rag/status", methods=["GET"])
def rag_status():
    """Get current RAG status"""
    return jsonify({"rag_enabled": is_rag_enabled()})


@app.route("/chat", methods=["POST"])
def chat():
    """
    main chat endpoint
    runs the constellation safety check flow
    """
    data = request.get_json()

    if not data or "message" not in data:
        return jsonify({"error": "message is required"}), 400

    query = data["message"]
    history = data.get("history", [])

    # run the async constellation flow
    result = asyncio.run(run_constellation(query, history))

    return jsonify(result)


# Select agents based on RAG mode
def get_nurse_draft(query, history):
    if is_rag_enabled():
        get_nurse_draft_langchain, _, _ = _get_langchain_funcs()
        return get_nurse_draft_langchain(query, history)
    return get_nurse_draft_fast(query, history)


def run_auditor(auditor_id, draft, query):
    if is_rag_enabled():
        _, run_auditor_langchain, _ = _get_langchain_funcs()
        return run_auditor_langchain(auditor_id, draft, query)
    return run_auditor_fast(auditor_id, draft, query)


def get_corrected_response(draft, audit_results, query, history):
    if is_rag_enabled():
        _, _, get_corrected_response_langchain = _get_langchain_funcs()
        return get_corrected_response_langchain(draft, audit_results, query, history)
    return get_corrected_response_fast(draft, audit_results, query, history)


@app.route("/chat/stream", methods=["POST"])
def chat_stream():
    """
    streaming chat endpoint - sends SSE events as each step completes
    this way frontend knows exactly when each auditor finishes
    """
    data = request.get_json()

    if not data or "message" not in data:
        return jsonify({"error": "message is required"}), 400

    query = data["message"]
    history = data.get("history", [])  # optional conversation history

    def generate():
        # run in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # step 1: drafting
            yield f"data: {json.dumps({'step': 'drafting', 'status': 'started'})}\n\n"

            draft = loop.run_until_complete(get_nurse_draft(query, history))

            yield f"data: {json.dumps({'step': 'drafting', 'status': 'complete', 'draft': draft})}\n\n"

            # step 2: determine which auditors to run
            active_auditors = get_active_auditors(query, history)

            # send the list of active auditors to frontend
            yield f"data: {json.dumps({'step': 'auditing', 'status': 'started', 'active_auditors': active_auditors})}\n\n"

            # organize auditors into stages for smart parallel execution:
            # Stage 1: Medical (always first - foundational safety)
            # Stage 2: Pediatric + Drug Interaction (parallel - specialized checks)
            # Stage 3: Legal + Empathy (parallel - polish/compliance)

            stage1 = [a for a in active_auditors if a == "medical"]
            stage2 = [a for a in active_auditors if a in [
                "pediatric", "drug_interaction"]]
            stage3 = [a for a in active_auditors if a in ["legal", "empathy"]]

            audit_results = {}

            # Stage 1: Medical audit first
            for auditor_id in stage1:
                yield f"data: {json.dumps({'step': f'{auditor_id}_check', 'status': 'started', 'auditor_id': auditor_id})}\n\n"
                result = loop.run_until_complete(
                    run_auditor(auditor_id, draft, query))
                audit_results[auditor_id] = result
                is_safe = result.get("status") == "SAFE"
                yield f"data: {json.dumps({'step': f'{auditor_id}_check', 'status': 'complete', 'auditor_id': auditor_id, 'result': result, 'safe': is_safe})}\n\n"

            # Stage 2: Pediatric + Drug Interaction in parallel
            if stage2:
                # mark all as started
                for auditor_id in stage2:
                    yield f"data: {json.dumps({'step': f'{auditor_id}_check', 'status': 'started', 'auditor_id': auditor_id})}\n\n"

                # run in parallel using asyncio.gather
                tasks = [run_auditor(a, draft, query) for a in stage2]
                results = loop.run_until_complete(asyncio.gather(*tasks))

                # send results
                for auditor_id, result in zip(stage2, results):
                    audit_results[auditor_id] = result
                    is_safe = result.get("status") == "SAFE"
                    yield f"data: {json.dumps({'step': f'{auditor_id}_check', 'status': 'complete', 'auditor_id': auditor_id, 'result': result, 'safe': is_safe})}\n\n"

            # Stage 3: Legal + Empathy in parallel
            if stage3:
                # mark all as started
                for auditor_id in stage3:
                    yield f"data: {json.dumps({'step': f'{auditor_id}_check', 'status': 'started', 'auditor_id': auditor_id})}\n\n"

                # run in parallel using asyncio.gather
                tasks = [run_auditor(a, draft, query) for a in stage3]
                results = loop.run_until_complete(asyncio.gather(*tasks))

                # send results
                for auditor_id, result in zip(stage3, results):
                    audit_results[auditor_id] = result
                    is_safe = result.get("status") == "SAFE"
                    yield f"data: {json.dumps({'step': f'{auditor_id}_check', 'status': 'complete', 'auditor_id': auditor_id, 'result': result, 'safe': is_safe})}\n\n"

            # step 3: determine if correction needed
            # correct if any auditor is unsafe OR if there are suggestions to incorporate
            needs_correction = any(
                r.get("status") != "SAFE" for r in audit_results.values()
            )
            has_suggestions = any(
                r.get("suggestion") for r in audit_results.values()
            )

            if needs_correction or has_suggestions:
                yield f"data: {json.dumps({'step': 'correcting', 'status': 'started'})}\n\n"

                final_response = loop.run_until_complete(
                    get_corrected_response(
                        draft, audit_results, query, history)
                )
                was_corrected = True

                yield f"data: {json.dumps({'step': 'correcting', 'status': 'complete'})}\n\n"
            else:
                final_response = draft
                was_corrected = False

            # always send finalizing step
            yield f"data: {json.dumps({'step': 'finalizing', 'status': 'started'})}\n\n"

            # build final result with all audit results
            audit_summary = {}
            for auditor_id, result in audit_results.items():
                audit_summary[auditor_id] = {
                    "safe": result.get("status") == "SAFE",
                    "reasoning": result.get("reasoning"),
                    "suggestion": result.get("suggestion"),
                    "name": AUDITOR_CONFIG[auditor_id]["name"]
                }

            # final result
            yield f"data: {json.dumps({'step': 'complete', 'result': {'draft': draft, 'audits': audit_summary, 'active_auditors': active_auditors, 'final_response': final_response, 'was_corrected': was_corrected}})}\n\n"

        finally:
            loop.close()

    return Response(generate(), mimetype='text/event-stream')


async def run_constellation(query: str, history: list = None) -> dict:
    """
    the main constellation flow (non-streaming):
    1. nurse drafts response
    2. auditors check in staged parallel execution
    3. if issues found, nurse fixes it
    """
    if history is None:
        history = []

    # step 1: get initial draft from nurse
    draft = await get_nurse_draft(query, history)

    # step 2: determine which auditors to run
    active_auditors = get_active_auditors(query, history)

    # organize auditors into stages for smart parallel execution
    stage1 = [a for a in active_auditors if a == "medical"]
    stage2 = [a for a in active_auditors if a in [
        "pediatric", "drug_interaction"]]
    stage3 = [a for a in active_auditors if a in ["legal", "empathy"]]

    audit_results = {}

    # Stage 1: Medical first
    for auditor_id in stage1:
        result = await run_auditor(auditor_id, draft, query)
        audit_results[auditor_id] = result

    # Stage 2: Pediatric + Drug Interaction in parallel
    if stage2:
        results = await asyncio.gather(*[run_auditor(a, draft, query) for a in stage2])
        for auditor_id, result in zip(stage2, results):
            audit_results[auditor_id] = result

    # Stage 3: Legal + Empathy in parallel
    if stage3:
        results = await asyncio.gather(*[run_auditor(a, draft, query) for a in stage3])
        for auditor_id, result in zip(stage3, results):
            audit_results[auditor_id] = result

    # check if we need corrections
    all_safe = all(r.get("status") == "SAFE" for r in audit_results.values())

    # step 3: if any flagged issues, get corrected response
    if all_safe:
        final_response = draft
        was_corrected = False
    else:
        final_response = await get_corrected_response(
            draft, audit_results, query, history
        )
        was_corrected = True

    # build response
    audit_summary = {}
    for auditor_id, result in audit_results.items():
        audit_summary[auditor_id] = {
            "safe": result.get("status") == "SAFE",
            "reasoning": result.get("reasoning"),
            "suggestion": result.get("suggestion") if result.get("status") != "SAFE" else None,
            "name": AUDITOR_CONFIG[auditor_id]["name"]
        }

    return {
        "draft": draft,
        "audits": audit_summary,
        "active_auditors": active_auditors,
        "final_response": final_response,
        "was_corrected": was_corrected
    }


if __name__ == "__main__":
    app.run(debug=True, port=5000)
