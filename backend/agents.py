import google.generativeai as genai
import asyncio
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from config import GEMINI_API_KEY, MODEL_NAME
from prompts import (
    PRIMARY_NURSE_PROMPT,
    CORRECTION_PROMPT,
    AUDITOR_CONFIG,
    get_active_auditors
)

# configure gemini
genai.configure(api_key=GEMINI_API_KEY)

# thread pool for running sync gemini calls async
executor = ThreadPoolExecutor(max_workers=5)

_thread_local = threading.local()


def _get_model(system_instruction: str | None):
    """Cache GenerativeModel per thread + system_instruction to reduce overhead."""
    cache = getattr(_thread_local, "models", None)
    if cache is None:
        cache = {}
        _thread_local.models = cache

    key = system_instruction or "__none__"
    model = cache.get(key)
    if model is None:
        model = genai.GenerativeModel(
            MODEL_NAME,
            system_instruction=system_instruction,
        )
        cache[key] = model
    return model


def _call_gemini(prompt: str, system_instruction: str = None) -> str:
    """sync wrapper for gemini api call"""
    model = _get_model(system_instruction)
    response = model.generate_content(prompt)
    return response.text


def parse_audit_response(response_text: str) -> dict:
    """parse json from auditor response, handle edge cases"""
    try:
        # try to extract json from the response
        # sometimes model wraps it in markdown
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            # remove markdown code blocks
            cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)

        return json.loads(cleaned)
    except json.JSONDecodeError:
        # fallback: if it looks safe, treat as safe
        if "SAFE" in response_text.upper() and "UNSAFE" not in response_text.upper():
            return {"status": "SAFE", "reasoning": "Response appears acceptable."}
        else:
            return {"status": "UNSAFE", "reasoning": response_text, "suggestion": "Review needed."}


async def call_gemini_async(prompt: str, system_instruction: str = None) -> str:
    """async wrapper using thread pool"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor,
        lambda: _call_gemini(prompt, system_instruction)
    )


async def get_nurse_draft(query: str, history: list = None) -> str:
    """get initial response from nurse agent"""
    if history and len(history) > 0:
        # format history for context
        history_text = "\n".join([
            f"{'Patient' if msg['role'] == 'user' else 'Nurse'}: {msg['content']}"
            for msg in history[-6:]  # last 6 messages for context
        ])
        prompt = f"Previous conversation:\n{history_text}\n\nPatient: {query}"
    else:
        prompt = query
    return await call_gemini_async(prompt, PRIMARY_NURSE_PROMPT)


async def run_auditor(auditor_id: str, draft: str, query: str) -> dict:
    """run a specific auditor, returns parsed dict with auditor_id"""
    config = AUDITOR_CONFIG[auditor_id]
    prompt = config["prompt"].format(draft=draft, query=query)
    response = await call_gemini_async(prompt)
    result = parse_audit_response(response)
    result["auditor_id"] = auditor_id
    result["auditor_name"] = config["name"]
    return result


async def get_corrected_response(draft: str, audit_results: dict, query: str, history: list = None) -> str:
    """ask nurse to fix the draft based on auditor feedback"""
    context = ""
    if history and len(history) > 0:
        history_text = "\n".join([
            f"{'Patient' if msg['role'] == 'user' else 'Nurse'}: {msg['content']}"
            for msg in history[-4:]
        ])
        context = f"Previous conversation:\n{history_text}\n\n"

    # build feedback section from all auditor results
    feedback_lines = []
    for auditor_id, result in audit_results.items():
        name = AUDITOR_CONFIG[auditor_id]["name"].upper()
        feedback = result.get("reasoning", "")
        if result.get("suggestion"):
            feedback += f" Suggestion: {result.get('suggestion')}"
        if result.get("status") == "SAFE":
            feedback = f"(Approved but with suggestion) {feedback}"
        feedback_lines.append(f"{name}: {feedback}")

    feedback_section = "\n".join(feedback_lines)

    prompt = CORRECTION_PROMPT.format(
        query=query,
        draft=draft,
        feedback_section=feedback_section
    )
    if context:
        prompt = context + prompt
    return await call_gemini_async(prompt, PRIMARY_NURSE_PROMPT)


# Keep these for backwards compatibility but mark as deprecated
async def run_medical_audit(draft: str, query: str) -> dict:
    """DEPRECATED: use run_auditor('medical', ...) instead"""
    return await run_auditor("medical", draft, query)


async def run_legal_audit(draft: str, query: str) -> dict:
    """DEPRECATED: use run_auditor('legal', ...) instead"""
    return await run_auditor("legal", draft, query)
