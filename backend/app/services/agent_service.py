"""
Multi-agent routing.

Router Agent
     |
-----------------------------------
|        |          |             |
HR    Legal     Technical     General

The "agents" here are not separate models — they're the same llm_service
call with (a) a department-specific system prompt and (b) retrieval
narrowed to that department's documents. That keeps Phase 2's LLM
abstraction as the single integration point instead of duplicating it.

classify_department() asks the LLM itself to route (cheap, one short
generation, no extra dependency). If the model returns anything
unparseable, we fail open to GENERAL rather than erroring the request.
"""
import logging

from app.models.user import Department
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

_ROUTER_PROMPT = """You are a routing classifier for an enterprise assistant.
Classify the user's question into exactly one category based on its subject matter:

HR - employee policies, benefits, leave, payroll, onboarding, workplace conduct
LEGAL - contracts, compliance, regulations, legal risk, terms, agreements
TECHNICAL - engineering, infrastructure, APIs, architecture, code, systems
GENERAL - anything else, or if it spans multiple categories

Respond with exactly one word: HR, LEGAL, TECHNICAL, or GENERAL. No punctuation, no explanation."""

_AGENT_SYSTEM_PROMPTS: dict[Department, str] = {
    Department.HR: (
        "You are the HR specialist agent for an enterprise assistant. "
        "Answer only using the provided context, drawn from HR and company-wide "
        "policy documents. Be precise about numbers (leave days, deadlines, "
        "eligibility). If information is unavailable in the context, say you "
        "don't know rather than guessing. Always cite the source document."
    ),
    Department.LEGAL: (
        "You are the Legal specialist agent for an enterprise assistant. "
        "Answer only using the provided context, drawn from legal and compliance "
        "documents. Be precise and conservative — do not extrapolate beyond what "
        "the documents state. Note that this is informational only and not legal "
        "advice. If information is unavailable in the context, say you don't know. "
        "Always cite the source document."
    ),
    Department.TECHNICAL: (
        "You are the Technical specialist agent for an enterprise assistant. "
        "Answer only using the provided context, drawn from engineering and "
        "technical documentation. Use precise technical language and include "
        "code or configuration snippets from the context where relevant. If "
        "information is unavailable in the context, say you don't know. Always "
        "cite the source document."
    ),
    Department.GENERAL: (
        "You are an enterprise AI assistant. Answer only using the provided "
        "context. If information is unavailable in the context, say you don't "
        "know. Always cite the source document."
    ),
}


async def classify_department(question: str) -> Department:
    try:
        raw = await llm_service.generate_answer(
            system_prompt=_ROUTER_PROMPT,
            user_prompt=question,
            max_tokens=10,
        )
    except Exception:
        logger.exception("Router agent classification failed, falling back to GENERAL")
        return Department.GENERAL

    cleaned = raw.strip().upper()
    for dept in Department:
        if dept.name in cleaned:
            return dept
    return Department.GENERAL


def get_system_prompt(department: Department) -> str:
    return _AGENT_SYSTEM_PROMPTS.get(department, _AGENT_SYSTEM_PROMPTS[Department.GENERAL])


def agent_name(department: Department) -> str:
    return f"{department.value}_agent"
