"""Deterministic classification logic mirroring classify_v1 / classify_v2.

Kept in lockstep with the real prompts (see pipeline/prompts/classify_v1.py
and classify_v2.py): v1 checks seniority before role function, so a senior
individual contributor (e.g. "Principal Software Engineer") gets
misclassified as decision_maker. v2 checks function first. This module is
what SimulatedLLMClient calls when no ANTHROPIC_API_KEY is configured, so
the zero-config demo path shows the same real, measurable v1->v2 accuracy
improvement that the eval suite records for the real-LLM path.
"""

from app.llm.keywords import matches_any_keyword

_TECHNICAL_KEYWORDS = [
    "engineer", "developer", "architect", "scientist", "devops", "sre",
    "programmer", "software", "data scientist", "machine learning",
]
_DECISION_TITLE_KEYWORDS = [
    "vp", "vice president", "director", "chief", "founder", "co-founder",
    "president", "head of", "owner", "ceo", "cto", "cfo", "coo", "cmo", "cpo",
]

_DECISION_SENIORITIES = {"exec", "senior"}


def _is_technical_title(title: str) -> bool:
    return matches_any_keyword(title.lower(), _TECHNICAL_KEYWORDS)


def _has_decision_title_keyword(title: str) -> bool:
    return matches_any_keyword(title.lower(), _DECISION_TITLE_KEYWORDS)


def classify_v1(profile: dict) -> dict:
    title = profile.get("title", "") or ""
    seniority = profile.get("seniority", "mid")

    if seniority in _DECISION_SENIORITIES:
        confidence = 0.9 if _has_decision_title_keyword(title) else 0.55
        return {
            "category": "decision_maker",
            "confidence": confidence,
            "reasoning": f"Seniority '{seniority}' treated as decision-making authority (v1 logic).",
        }
    if _is_technical_title(title):
        return {
            "category": "technical",
            "confidence": 0.85,
            "reasoning": f"Title '{title}' matches a hands-on technical role.",
        }
    return {
        "category": "not_relevant",
        "confidence": 0.7,
        "reasoning": f"Title '{title}' has no technical or decision-making signal.",
    }


def classify_v2(profile: dict) -> dict:
    title = profile.get("title", "") or ""
    seniority = profile.get("seniority", "mid")

    if _is_technical_title(title):
        return {
            "category": "technical",
            "confidence": 0.85,
            "reasoning": f"Title '{title}' is a hands-on technical role regardless of seniority.",
        }
    if seniority in _DECISION_SENIORITIES:
        confidence = 0.9 if _has_decision_title_keyword(title) else 0.55
        return {
            "category": "decision_maker",
            "confidence": confidence,
            "reasoning": f"Non-technical '{seniority}'-level role with likely budget authority.",
        }
    return {
        "category": "not_relevant",
        "confidence": 0.7,
        "reasoning": f"Title '{title}' has no technical or decision-making signal.",
    }


def simulate_classification(profile: dict, prompt_version: str) -> dict:
    if prompt_version == "classify_v1":
        return classify_v1(profile)
    if prompt_version == "classify_v2":
        return classify_v2(profile)
    raise ValueError(f"SimulatedLLMClient: unknown classify prompt_version {prompt_version!r}")
