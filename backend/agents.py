import google.generativeai as genai
import asyncio
import json
import re
from concurrent.futures import ThreadPoolExecutor
from config import GEMINI_API_KEY, MODEL_NAME
from prompts import PRIMARY_NURSE_PROMPT, MEDICAL_AUDITOR_PROMPT, LEGAL_AUDITOR_PROMPT, CORRECTION_PROMPT

# configure gemini
genai.configure(api_key=GEMINI_API_KEY)

# thread pool for running sync gemini calls async
executor = ThreadPoolExecutor(max_workers=3)


def _call_gemini(prompt: str, system_instruction: str = None) -> str:
    """sync wrapper for gemini api call"""
    model = genai.GenerativeModel(
        MODEL_NAME,
        system_instruction=system_instruction
    )
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


async def run_medical_audit(draft: str, query: str) -> dict:
    """run medical safety check, returns parsed dict"""
    prompt = MEDICAL_AUDITOR_PROMPT.format(draft=draft, query=query)
    response = await call_gemini_async(prompt)
    return parse_audit_response(response)


async def run_legal_audit(draft: str, query: str) -> dict:
    """run legal/compliance check, returns parsed dict"""
    prompt = LEGAL_AUDITOR_PROMPT.format(draft=draft, query=query)
    response = await call_gemini_async(prompt)
    return parse_audit_response(response)


async def get_corrected_response(draft: str, medical_feedback: str, legal_feedback: str, query: str, history: list = None) -> str:
    """ask nurse to fix the draft based on auditor feedback"""
    context = ""
    if history and len(history) > 0:
        history_text = "\n".join([
            f"{'Patient' if msg['role'] == 'user' else 'Nurse'}: {msg['content']}"
            for msg in history[-4:]
        ])
        context = f"Previous conversation:\n{history_text}\n\n"

    prompt = CORRECTION_PROMPT.format(
        query=query,
        draft=draft,
        medical_feedback=medical_feedback,
        legal_feedback=legal_feedback
    )
    if context:
        prompt = context + prompt
    return await call_gemini_async(prompt, PRIMARY_NURSE_PROMPT)
