from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import asyncio
import json
from config import FRONTEND_URL
from agents import (
    get_nurse_draft,
    run_medical_audit,
    run_legal_audit,
    get_corrected_response
)

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
    return jsonify({"status": "ok", "message": "constellation is running"})


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

    # run the async constellation flow
    result = asyncio.run(run_constellation(query))

    return jsonify(result)


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

            # step 2: run auditors in parallel but report as each completes
            yield f"data: {json.dumps({'step': 'auditing', 'status': 'started'})}\n\n"

            # create tasks
            medical_task = run_medical_audit(draft, query)
            legal_task = run_legal_audit(draft, query)

            # run both and collect results
            medical_result, legal_result = loop.run_until_complete(
                asyncio.gather(medical_task, legal_task)
            )

            # send medical result
            medical_safe = medical_result.get("status") == "SAFE"
            yield f"data: {json.dumps({'step': 'medical_check', 'status': 'complete', 'result': medical_result, 'safe': medical_safe})}\n\n"

            # send legal result
            legal_safe = legal_result.get("status") == "SAFE"
            yield f"data: {json.dumps({'step': 'legal_check', 'status': 'complete', 'result': legal_result, 'safe': legal_safe})}\n\n"

            # step 3: determine if correction needed
            # correct if either is unsafe OR if there are suggestions to incorporate
            needs_correction = not medical_safe or not legal_safe
            has_suggestions = (medical_result.get(
                "suggestion") or legal_result.get("suggestion"))

            if needs_correction or has_suggestions:
                yield f"data: {json.dumps({'step': 'correcting', 'status': 'started'})}\n\n"

                # gather all feedback including suggestions
                medical_feedback = medical_result.get('reasoning', '')
                if medical_result.get('suggestion'):
                    medical_feedback += f" Suggestion: {medical_result.get('suggestion')}"
                if medical_safe:
                    medical_feedback = f"(Approved but with suggestion) {medical_feedback}"

                legal_feedback = legal_result.get('reasoning', '')
                if legal_result.get('suggestion'):
                    legal_feedback += f" Suggestion: {legal_result.get('suggestion')}"
                if legal_safe:
                    legal_feedback = f"(Approved but with suggestion) {legal_feedback}"

                final_response = loop.run_until_complete(
                    get_corrected_response(
                        draft, medical_feedback, legal_feedback, query, history)
                )
                was_corrected = True

                yield f"data: {json.dumps({'step': 'correcting', 'status': 'complete'})}\n\n"
            else:
                final_response = draft
                was_corrected = False

            # always send finalizing step
            yield f"data: {json.dumps({'step': 'finalizing', 'status': 'started'})}\n\n"

            # final result
            yield f"data: {json.dumps({'step': 'complete', 'result': {'draft': draft, 'medical_audit': {'safe': medical_safe, 'reasoning': medical_result.get('reasoning'), 'suggestion': medical_result.get('suggestion')}, 'legal_audit': {'safe': legal_safe, 'reasoning': legal_result.get('reasoning'), 'suggestion': legal_result.get('suggestion')}, 'final_response': final_response, 'was_corrected': was_corrected}})}\n\n"

        finally:
            loop.close()

    return Response(generate(), mimetype='text/event-stream')


async def run_constellation(query: str) -> dict:
    """
    the main constellation flow (non-streaming):
    1. nurse drafts response
    2. auditors check in parallel
    3. if issues found, nurse fixes it
    """

    # step 1: get initial draft from nurse
    draft = await get_nurse_draft(query)

    # step 2: run both auditors in parallel
    medical_result, legal_result = await asyncio.gather(
        run_medical_audit(draft, query),
        run_legal_audit(draft, query)
    )

    # check if we need corrections
    medical_safe = medical_result.get("status") == "SAFE"
    legal_safe = legal_result.get("status") == "SAFE"

    # step 3: if either flagged issues, get corrected response
    if medical_safe and legal_safe:
        final_response = draft
        was_corrected = False
    else:
        medical_feedback = f"{medical_result.get('reasoning', '')} {medical_result.get('suggestion', '')}" if not medical_safe else "No issues."
        legal_feedback = f"{legal_result.get('reasoning', '')} {legal_result.get('suggestion', '')}" if not legal_safe else "No issues."

        final_response = await get_corrected_response(
            draft, medical_feedback, legal_feedback, query
        )
        was_corrected = True

    return {
        "draft": draft,
        "medical_audit": {
            "safe": medical_safe,
            "reasoning": medical_result.get("reasoning"),
            "suggestion": medical_result.get("suggestion") if not medical_safe else None
        },
        "legal_audit": {
            "safe": legal_safe,
            "reasoning": legal_result.get("reasoning"),
            "suggestion": legal_result.get("suggestion") if not legal_safe else None
        },
        "final_response": final_response,
        "was_corrected": was_corrected
    }


if __name__ == "__main__":
    app.run(debug=True, port=5000)
