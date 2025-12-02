# Constellation Backend

Flask backend for the Constellation multi-agent safety system.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Add your GEMINI_API_KEY to .env

python app.py
```

## API Endpoints

### POST /chat

Send a message and get a safety-checked response.

Request:

```json
{
	"message": "What can I do for a headache?"
}
```

Response:

```json
{
	"draft": "Initial nurse response...",
	"medical_audit": {
		"safe": true,
		"feedback": null
	},
	"legal_audit": {
		"safe": true,
		"feedback": null
	},
	"final_response": "Final safe response...",
	"was_corrected": false
}
```

### GET /health

Health check endpoint.

## Deploy on Render

1. Create Web Service
2. Build command: `pip install -r requirements.txt`
3. Start command: `gunicorn app:app`
4. Add env vars: `GEMINI_API_KEY`, `FRONTEND_URL`
