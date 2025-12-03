from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import asyncio
import json
from config import FRONTEND_URL
from agents import (
    get_nurse_draft,
    run_auditor,
    get_corrected_response
)
from prompts import get_active_auditors, AUDITOR_CONFIG

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
    history = data.get("history", [])

    # run the async constellation flow
    result = asyncio.run(run_constellation(query, history))

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
