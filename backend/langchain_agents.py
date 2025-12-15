"""
LangChain-based agent orchestration for the Constellation safety system.
This wraps our existing agent logic in LangChain abstractions for better
composability and to demonstrate LangChain integration skills.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnablePassthrough
from typing import Optional
import asyncio
import json
import re

from config import GEMINI_API_KEY, MODEL_NAME
from prompts import (
    PRIMARY_NURSE_PROMPT,
    CORRECTION_PROMPT,
    AUDITOR_CONFIG,
    get_active_auditors
)
from rag import get_relevant_context


# Initialize LangChain LLM
llm = ChatGoogleGenerativeAI(
    model=MODEL_NAME,
    google_api_key=GEMINI_API_KEY,
    temperature=0.7,
)

# Lower temperature for auditors (more consistent)
auditor_llm = ChatGoogleGenerativeAI(
    model=MODEL_NAME,
    google_api_key=GEMINI_API_KEY,
    temperature=0.3,
)


def parse_audit_json(response_text: str) -> dict:
    """Parse JSON from auditor response, handle edge cases"""
    try:
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
        return json.loads(cleaned)
    except json.JSONDecodeError:
        if "SAFE" in response_text.upper() and "UNSAFE" not in response_text.upper():
            return {"status": "SAFE", "reasoning": "Response appears acceptable."}
        else:
            return {"status": "UNSAFE", "reasoning": response_text, "suggestion": "Review needed."}


def format_history(history: list) -> list:
    """Convert history to LangChain message format"""
    messages = []
    for msg in history[-6:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    return messages


async def get_nurse_draft_langchain(query: str, history: list = None) -> str:
    """
    Generate nurse draft using LangChain with optional RAG context.
    """
    # Check if we have relevant documents in RAG
    rag_context = get_relevant_context(query)

    # Build the prompt with optional RAG context
    system_prompt = PRIMARY_NURSE_PROMPT
    if rag_context:
        system_prompt += f"\n\nRelevant medical reference information:\n{rag_context}\n\nUse this reference information to provide more accurate advice when relevant."

    # Build conversation history
    history_text = ""
    if history and len(history) > 0:
        history_text = "\n".join([
            f"{'Patient' if msg['role'] == 'user' else 'Nurse'}: {msg['content']}"
            for msg in history[-6:]
        ])
        history_text = f"Previous conversation:\n{history_text}\n\n"

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{history}Patient: {query}")
    ])

    chain = prompt | llm

    # Run async
    response = await chain.ainvoke({
        "history": history_text,
        "query": query
    })

    return response.content


async def run_auditor_langchain(auditor_id: str, draft: str, query: str) -> dict:
    """
    Run a specific auditor using LangChain.
    Returns parsed dict with auditor_id.
    """
    config = AUDITOR_CONFIG[auditor_id]

    prompt = ChatPromptTemplate.from_messages([
        ("human", config["prompt"])
    ])

    chain = prompt | auditor_llm

    response = await chain.ainvoke({
        "draft": draft,
        "query": query
    })

    result = parse_audit_json(response.content)
    result["auditor_id"] = auditor_id
    result["auditor_name"] = config["name"]
    return result


async def get_corrected_response_langchain(
    draft: str,
    audit_results: dict,
    query: str,
    history: list = None
) -> str:
    """
    Generate corrected response using LangChain based on auditor feedback.
    """
    # Build context from history
    context = ""
    if history and len(history) > 0:
        history_text = "\n".join([
            f"{'Patient' if msg['role'] == 'user' else 'Nurse'}: {msg['content']}"
            for msg in history[-4:]
        ])
        context = f"Previous conversation:\n{history_text}\n\n"

    # Build feedback section from all auditor results
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

    # Use LangChain prompt template
    correction_template = CORRECTION_PROMPT.replace("{query}", "{query_text}")
    correction_template = correction_template.replace(
        "{draft}", "{draft_text}")
    correction_template = correction_template.replace(
        "{feedback_section}", "{feedback}")

    prompt = ChatPromptTemplate.from_messages([
        ("system", PRIMARY_NURSE_PROMPT),
        ("human", "{context}" + correction_template)
    ])

    chain = prompt | llm

    response = await chain.ainvoke({
        "context": context,
        "query_text": query,
        "draft_text": draft,
        "feedback": feedback_section
    })

    return response.content


# Staged parallel execution using LangChain
async def run_constellation_langchain(query: str, history: list = None) -> dict:
    """
    Run the full constellation flow using LangChain agents.
    Uses staged parallel execution with asyncio.gather.
    """
    if history is None:
        history = []

    # Step 1: Get nurse draft (with RAG context if available)
    draft = await get_nurse_draft_langchain(query, history)

    # Step 2: Determine which auditors to run
    active_auditors = get_active_auditors(query, history)

    # Organize into stages
    stage1 = [a for a in active_auditors if a == "medical"]
    stage2 = [a for a in active_auditors if a in [
        "pediatric", "drug_interaction"]]
    stage3 = [a for a in active_auditors if a in ["legal", "empathy"]]

    audit_results = {}

    # Stage 1: Medical first
    for auditor_id in stage1:
        result = await run_auditor_langchain(auditor_id, draft, query)
        audit_results[auditor_id] = result

    # Stage 2: Pediatric + Drug Interaction in parallel
    if stage2:
        results = await asyncio.gather(*[
            run_auditor_langchain(a, draft, query) for a in stage2
        ])
        for auditor_id, result in zip(stage2, results):
            audit_results[auditor_id] = result

    # Stage 3: Legal + Empathy in parallel
    if stage3:
        results = await asyncio.gather(*[
            run_auditor_langchain(a, draft, query) for a in stage3
        ])
        for auditor_id, result in zip(stage3, results):
            audit_results[auditor_id] = result

    # Check if correction needed
    all_safe = all(r.get("status") == "SAFE" for r in audit_results.values())
    has_suggestions = any(r.get("suggestion") for r in audit_results.values())

    if all_safe and not has_suggestions:
        final_response = draft
        was_corrected = False
    else:
        final_response = await get_corrected_response_langchain(
            draft, audit_results, query, history
        )
        was_corrected = True

    # Build response
    audit_summary = {}
    for auditor_id, result in audit_results.items():
        audit_summary[auditor_id] = {
            "safe": result.get("status") == "SAFE",
            "reasoning": result.get("reasoning"),
            "suggestion": result.get("suggestion"),
            "name": AUDITOR_CONFIG[auditor_id]["name"]
        }

    return {
        "draft": draft,
        "audits": audit_summary,
        "active_auditors": active_auditors,
        "final_response": final_response,
        "was_corrected": was_corrected,
        "rag_used": get_relevant_context(query) is not None
    }
