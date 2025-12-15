<img src="./frontend/public/constellation.svg" width="64" height="64" alt="constellation icon" />

# polaris-lite: multi-agent safety ai chatbot

a multi-agent safety ai chatbot system for healthcare that uses multiple specialized auditors to verify and correct responses before they reach users. built with **LangChain** for agent orchestration, **ChromaDB** for RAG (retrieval-augmented generation), and a flask backend (making calls to the gemini api) with a next.js frontend.

hosted and running on [vercel](https://polaris-lite.vercel.app/)

<p align="center">
  <img src="./frontend/public/demo.gif" alt="demo" width="800"/>
  <br/>
</p>

> [!NOTE]
> initial load time may be slow as the backend wakes up from idling on render.com

## feature overview

- multi-agent constellation architecture based on [polaris](https://hippocraticai.com/polaris-3/) with dynamic auditor selection
- **optional RAG mode** with LangChain + ChromaDB - toggle on for knowledge-enhanced responses (off by default for speed)
- **pre-populated medical knowledge base** with OTC dosing, pediatric safety, drug interactions, emergency signs
- **HuggingFace Transformers** embeddings (all-MiniLM-L6-v2) for semantic document retrieval
- **5 specialized auditors**: medical, legal, empathy (always run), plus pediatric and drug interaction (if keywords detected)
- real-time SSE streaming of the reasoning chain as each agent processes in sequence/parallel
- human-in-the-loop (hitl) mode for manual approval of safety corrections with edit capability
- visual diff view showing exactly what was changed and why
- chat history with local storage persistence
- document upload UI for custom RAG knowledge base
- light/dark mode toggle

## how it works

the system uses a "constellation" of specialized ai agents that work together:

| Agent                        | Role                                                                                                    | When it runs                        |
| ---------------------------- | ------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| **Nurse Agent**              | Drafts initial responses to health questions. Intentionally imperfect to demonstrate the safety system. | Always                              |
| **Medical Auditor**          | Reviews drafts for medical accuracy, dangerous dosage info, missing disclaimers, urgency issues.        | Always                              |
| **Legal Auditor**            | Reviews drafts for compliance issues, liability concerns, scope-of-practice violations.                 | Always                              |
| **Empathy Auditor**          | Checks if the response is warm, reassuring, and appropriate for anxious patients.                       | Always                              |
| **Pediatric Auditor**        | Specialized checks for child-specific safety (dosing, contraindications, age-appropriate care).         | When children/pregnancy mentioned   |
| **Drug Interaction Auditor** | Checks for dangerous drug interactions when multiple medications are discussed.                         | When multiple medications mentioned |
| **Correction Agent**         | If auditors flag issues, this agent rewrites the response incorporating their feedback.                 | When any auditor flags an issue     |

the auditors run in **staged parallel execution** using `asyncio.gather` for optimal performance:

1. **Stage 1**: Medical Auditor (runs first - foundational safety check)
2. **Stage 2**: Pediatric + Drug Interaction (run in parallel if triggered)
3. **Stage 3**: Legal + Empathy (run in parallel - polish/compliance)

conditional auditors are triggered by keyword detection in the user's message and conversation history.

## stuff used

- [LangChain](https://langchain.com/) - agent orchestration and prompt chaining
- [ChromaDB](https://www.trychroma.com/) - vector store for RAG document embeddings
- [sentence-transformers](https://www.sbert.net/) - local embeddings (all-MiniLM-L6-v2) for document retrieval
- [gemini api](https://developers.generativeai.google/products/gemini) - gemini-2.0-flash model for all agents
- [flask](https://flask.palletsprojects.com/) for the backend api with sse streaming
- [gunicorn](https://gunicorn.org/) for running the flask server in production
- [next.js 16](https://nextjs.org/) with react 19 for the frontend
- [shadcn/ui](https://ui.shadcn.com/) with tailwind css v4 for prebuilt components
- [render.com](https://render.com/) for hosting the backend api
- [vercel](https://vercel.com/) for hosting the frontend app

## workflow

1. user asks a health-related question
2. nurse agent drafts an initial response (intentionally may be imperfect)
3. system detects which auditors should run based on keywords in the prompt
4. auditors review the draft **sequentially** - you see each one process in real-time
5. if issues are found, the correction agent rewrites the response
6. user sees the full reasoning chain and final (safe) response
7. in hitl mode, user can approve/reject/edit corrections before they're applied

## dynamic auditor activation

the system intelligently activates additional auditors based on your prompt:

**pediatric auditor activates on keywords like:**

- child, children, kid, baby, infant, toddler, newborn
- son, daughter, pregnant, pregnancy, breastfeeding
- "2 year old", "6 month old", teenager, adolescent

**drug interaction auditor activates on keywords like:**

- medication, medicine, drug, prescription, pill
- specific drug names (ibuprofen, tylenol, aspirin, etc.)
- mix, combine, together, interaction

this means asking "what's a good headache remedy?" will run 3 auditors, but asking "what's the right tylenol dose for my 2 year old who's also on antibiotics?" will run all 5!

## limitations

now obviously this is a demo/proof-of-concept without real medical oversight - do not use this for actual medical advice! the nurse agent is intentionally imperfect to demonstrate the safety system actually doing something. the auditors may not catch all issues, and the correction agent may not always produce perfect responses. this is just to showcase the multi-agent safety architecture and ui features.

the rag feature uses an in-memory chromadb store which resets on server restart. for production, you'd want persistent storage and more sophisticated document processing.

## rag document upload

you can enhance the nurse agent's responses by uploading medical reference documents:

1. open the sidebar and expand "RAG Documents"
2. upload a PDF file (drag & drop or click to browse)
3. the document is automatically chunked and embedded using sentence-transformers
4. when you ask questions, relevant context is retrieved and included in the nurse's prompt
5. you can see which documents are loaded and remove them anytime

this is useful for:
- adding specific medical guidelines (dosage charts, drug interaction tables)
- including institutional protocols or policies
- referencing research papers or clinical guidelines

## screenshots

1. chat interface with reasoning chain visible
   <img width="1512" height="950" alt="image" src="https://github.com/user-attachments/assets/a74e6d8f-281e-4662-acbb-33dedb6f06be" />

2. safety correction in action - auditors flagging issues
   <img width="1512" height="950" alt="image" src="https://github.com/user-attachments/assets/d4af0f6b-367f-416a-a5c2-a97a2131f3e1" />

3. hitl mode - human approval with edit capability
   <img width="1512" height="950" alt="image" src="https://github.com/user-attachments/assets/5268620d-254c-47a0-9590-1604740651fb" />

## example prompts to try

these prompts could be helpful to trigger different auditor combinations:

**3 auditors (medical, legal, empathy):**

- "I have a headache, what should I take?"
- "How do I know if I have a cold or the flu?"

**4 auditors (+pediatric):**

- "What's the right Tylenol dose for my 2 year old?" - triggers pediatric safety
- "My daughter has a fever, when should I worry?" - triggers pediatric context
- "Is it safe to breastfeed while taking ibuprofen?" - triggers pregnancy/nursing check

**5 auditors (+drug interaction):**

- "Can I take ibuprofen and aspirin together for pain?" - triggers drug interaction
- "My child is on antibiotics, can I give her children's Motrin too?" - triggers BOTH pediatric AND drug interaction
- "I'm taking blood pressure medication, is it safe to take Advil?" - triggers drug interaction

## setup instructions

### backend

1. cd into the `backend` folder
2. create a virtual environment: `uv venv .venv`
3. activate the virtual environment:
   - on mac/linux: `source .venv/bin/activate`
   - on windows: `.venv\Scripts\activate`
4. install dependencies: `pip install -r requirements.txt`
5. copy the `.env.example` file to `.env` and add your gemini api key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```
6. run the backend server: `uv run app.py`
7. the backend api will be running at `http://localhost:5000`

### frontend

1. cd into the `frontend` folder
2. install dependencies: `npm install`
3. create `.env.local` with backend url:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:5000
   ```
4. run the frontend dev server: `npm run dev`
5. the frontend app will be running at `http://localhost:3000`

## deployment

### backend (render.com)

1. create a new web service on render
2. connect your github repo
3. set build command: `pip install -r requirements.txt`
4. set start command: `gunicorn app:app`
5. add environment variable: `GEMINI_API_KEY`

### frontend (vercel)

1. import your github repo to vercel
2. set root directory to `frontend`
3. add environment variable: `NEXT_PUBLIC_API_URL` pointing to your render backend
4. deploy

## architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                             │
│  Next.js + React + shadcn/ui + Tailwind                     │
│  - Chat interface with message history                      │
│  - Real-time process log via SSE                            │
│  - Dynamic auditor list based on prompt                     │
│  - HITL approval panel with edit capability                 │
│  - Diff view for corrections                                │
│  - Document upload UI for RAG                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ SSE Stream
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        Backend                              │
│  Flask + LangChain + Gunicorn                               │
│  /chat/stream - SSE endpoint                                │
│  /documents/upload - PDF upload for RAG                     │
│  Dynamic auditor selection + staged parallel execution      │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     │
┌───────────────┐     ┌───────────────┐             │
│   ChromaDB    │     │     Nurse     │             │
│  Vector Store │────▶│     Agent     │◀── LangChain
│  (RAG Context)│     │  (LangChain)  │     Prompts
└───────────────┘     └───────┬───────┘             │
        ▲                     │                     │
        │                     │                     │
   PDF Upload                 │                     │
  (sentence-transformers)     │                     │
                              │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   │                   │
   ┌─────────┐              │                   │
   │ Stage 1 │              │                   │
   │   Med   │ (sequential) │                   │
   └────┬────┘              │                   │
        │                   │                   │
        ▼                   │                   │
   ┌─────────────────┐      │                   │
   │     Stage 2     │      │                   │
   │    Ped ║  Drug  │ (parallel via asyncio.gather)
   │  (if triggered) │      │                   │
   └────────┬────────┘      │                   │
            │               │                   │
            ▼               │                   │
   ┌─────────────────┐      │                   │
   │     Stage 3     │      │                   │
   │  Legal ║   Emp  │ (parallel via asyncio.gather)
   └────────┬────────┘      │                   │
            │               │                   │
            ▼               │                   │
    ┌───────────────────────┴───────────────────┐
    │         Correction Agent                  │
    │       (if any issues flagged)             │
    └───────────────────────────────────────────┘
                            │
                            ▼
                      Gemini API
```

## api endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with feature status |
| `/chat` | POST | Non-streaming chat endpoint |
| `/chat/stream` | POST | SSE streaming chat endpoint |
| `/documents/upload` | POST | Upload PDF for RAG |
| `/documents` | GET | List uploaded documents |
| `/documents/<doc_id>` | DELETE | Delete a document |
| `/documents/clear` | POST | Clear all documents |

## license

mit
