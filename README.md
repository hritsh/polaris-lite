<img src="./frontend/public/constellation.svg" width="64" height="64" alt="constellation icon" />

# polaris-lite: multi-agent safety ai chatbot

a multi-agent safety ai chatbot system for healthcare that uses multiple specialized auditors to verify and correct responses before they reach users. it uses a flask backend (making calls to the gemini api) and a next.js frontend.

<p align="center">
  <img src="./frontend/public/demo.gif" alt="demo" width="800"/>
  <br/>
</p>

hosted and running on [vercel](https://polaris-lite.vercel.app/)

> [!NOTE]
> initial load time may be slow as the backend wakes up from idling on render.com

## feature overview

- multi-agent constellation architecture based on [hippocratic ai's polaris](https://hippocraticai.com/polaris-3/) with nurse agent, medical auditor, and legal auditor
- real-time streaming of the reasoning chain as each agent processes the request
- human-in-the-loop (hitl) mode for manual approval of safety corrections with edit capability
- visual diff view showing exactly what was changed and why
- chat history with local storage persistence
- light/dark mode toggle

## how it works

the system uses a "constellation" of specialized ai agents that work together:

| Agent                | Role                                                                                                    |
| -------------------- | ------------------------------------------------------------------------------------------------------- |
| **Nurse Agent**      | Drafts initial responses to health questions. Intentionally imperfect to demonstrate the safety system. |
| **Medical Auditor**  | Reviews drafts for medical accuracy, dangerous dosage info, missing disclaimers, urgency issues.        |
| **Legal Auditor**    | Reviews drafts for compliance issues, liability concerns, scope-of-practice violations.                 |
| **Correction Agent** | If auditors flag issues, this agent rewrites the response incorporating their feedback.                 |

the auditors run in parallel using `asyncio.gather` for faster processing, and results stream back to the frontend in real-time via server-sent events (sse).

## stuff used

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
3. medical and legal auditors review the draft in parallel
4. if issues are found, the correction agent rewrites the response
5. user sees the full reasoning chain and final (safe) response
6. in hitl mode, user can approve/reject/edit corrections before they're applied

## limitations

now obviously this is a demo/proof-of-concept without real medical oversight - do not use this for actual medical advice! the nurse agent is intentionally imperfect to demonstrate the safety system actually doing something. the auditors may not catch all issues, and the correction agent may not always produce perfect responses. this is just to showcase the multi-agent safety architecture and ui features.

actual future work could involve training specialized models for each agent, integrating real medical knowledge bases using retrieval-augmented generation (rag), and involving real medical professionals in the loop, like hippocratic ai is doing with polaris.

## screenshots

1. chat interface with reasoning chain visible
   <img width="1512" alt="chat view" src="https://github.com/user-attachments/assets/placeholder1.png" />

2. safety correction in action - auditors flagging issues
   <img width="1512" alt="safety correction" src="https://github.com/user-attachments/assets/placeholder2.png" />

3. hitl mode - human approval with edit capability
   <img width="1512" alt="hitl mode" src="https://github.com/user-attachments/assets/placeholder3.png" />

## example prompts to try

these prompts could be helpful to trigger the safety auditors and see the system in action:

- "What's the right Tylenol dose for my 2 year old?" - triggers dosage safety flags
- "Can I take my husband's blood pressure medication?" - triggers prescription safety flags
- "I've been having chest pains for 3 days, what should I do?" - triggers urgency flags
- "Is it safe to mix ibuprofen and aspirin for pain?" - triggers drug interaction flags

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
│  - HITL approval panel with edit capability                 │
│  - Diff view for corrections                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ SSE Stream
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        Backend                              │
│  Flask + Gunicorn                                           │
│  /chat/stream - SSE endpoint                                │
└─────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
    ┌───────────┐     ┌───────────┐     ┌───────────┐
    │   Nurse   │     │  Medical  │     │   Legal   │
    │   Agent   │────▶│  Auditor  │     │  Auditor  │
    │           │     │           │     │           │
    └───────────┘     └─────┬─────┘     └─────┬─────┘
                            │                 │
                            │   parallel      │
                            ▼                 ▼
                      ┌───────────────────────────┐
                      │    Correction Agent       │
                      │  (if issues flagged)      │
                      └───────────────────────────┘
                                    │
                                    ▼
                              Gemini API
```

## license

mit
