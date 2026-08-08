"""Deterministic, rule-based stand-in for a real LLM.

Used automatically when no ANTHROPIC_API_KEY is configured (see
`get_llm_client()` in client.py) so the whole pipeline and eval suite run
end to end with zero setup. It implements the exact same `LLMClient`
interface as the real Anthropic client — system+user text in, text out —
and "reads" the same rendered prompts a real model would: it finds the bio
inside the extract prompt's triple-quoted Bio block, and the upstream
ExtractedProfile JSON embedded in the classify prompt, using the same
delimiters the prompt templates always render.

This is intentionally simple keyword/regex heuristics, not a real model —
the point is a reproducible, zero-config fallback with genuinely different
behavior between classify_v1 and classify_v2 (see classify_v1.py /
classify_v2.py for what the difference is and why), not to be a good
information extractor in general.
"""

import json
import re

from app.llm.client import LLMClient
from app.llm.keywords import matches_any_keyword

_PROMPT_VERSION_RE = re.compile(r"\[prompt_version=(\S+?)\]")
_BIO_RE = re.compile(r'Bio:\s*"""\s*(.*?)\s*"""', re.DOTALL)
_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)

_IS_A_RE = re.compile(
    r"\bis\s+(?:a|an)\s+(?P<title>[A-Z][^,.\n]*?)\s+(?:at|@)\s+"
    r"(?P<company>[A-Z][\w&.'-]*(?:\s+[A-Z][\w&.'-]*){0,3})"
)
_SEP_RE = re.compile(
    r"[,\-–—]\s*(?:is\s+(?:a|an)\s+)?(?P<title>[A-Z][^,.\n]*?)\s+(?:at|@)\s+"
    r"(?P<company>[A-Z][\w&.'-]*(?:\s+[A-Z][\w&.'-]*){0,3})"
)

_EXEC_KEYWORDS = [
    "chief executive", "chief technology", "chief financial", "chief operating",
    "chief marketing", "chief product", "chief", "ceo", "cto", "cfo", "coo", "cmo", "cpo",
    "vice president", "vp", "president", "founder", "co-founder", "head of", "owner",
]
_SENIOR_KEYWORDS = ["senior", "sr.", "lead", "principal", "staff", "director", "manager"]
_JUNIOR_KEYWORDS = ["junior", "jr.", "intern", "entry-level", "entry level", "associate"]

INDUSTRY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("fintech", ["fintech", "banking", "payments", "financial services"]),
    ("healthcare", ["healthcare", "health tech", "medical", "biotech", "pharma"]),
    ("e-commerce", ["e-commerce", "ecommerce", "online marketplace", "online store"]),
    ("retail", ["retail"]),
    ("saas", ["saas", "software as a service", "b2b software"]),
    ("education", ["education", "edtech", "university"]),
    ("manufacturing", ["manufacturing", "industrial", "factory"]),
    ("logistics", ["logistics", "supply chain", "freight", "shipping"]),
    ("cybersecurity", ["cybersecurity", "infosec", "security"]),
    ("gaming", ["gaming", "video game", "game studio"]),
    ("media", ["entertainment", "streaming", "publishing", "film studio", "record label", "news outlet"]),
    ("energy", ["renewable energy", "energy", "solar", "oil and gas"]),
    ("real estate", ["real estate", "property management"]),
    ("insurance", ["insurance", "insurtech"]),
    ("legal", ["legal", "law firm", "legaltech"]),
    ("telecom", ["telecom", "telecommunications"]),
    ("automotive", ["automotive", "vehicles"]),
    ("marketing", ["adtech", "ad tech", "marketing agency", "advertising agency"]),
    ("nonprofit", ["nonprofit", "non-profit", "ngo"]),
    ("government", ["government", "public sector"]),
    ("consulting", ["consulting", "advisory"]),
    ("hospitality", ["hospitality", "hotel", "travel"]),
]


def _extract_prompt_version(system: str) -> str:
    match = _PROMPT_VERSION_RE.search(system)
    if not match:
        raise ValueError("SimulatedLLMClient: system prompt has no [prompt_version=...] marker")
    return match.group(1)


def _extract_bio_from_user(user: str) -> str:
    match = _BIO_RE.search(user)
    return match.group(1).strip() if match else user.strip()


def _extract_json_object_from_user(user: str) -> dict:
    match = _JSON_OBJECT_RE.search(user)
    if not match:
        raise ValueError("SimulatedLLMClient: no JSON object found in user prompt")
    return json.loads(match.group(0))


def extract_title_company(bio: str) -> tuple[str, str]:
    for pattern in (_IS_A_RE, _SEP_RE):
        match = pattern.search(bio)
        if match:
            title = match.group("title").strip().rstrip(".,")
            company = match.group("company").strip().rstrip(".,")
            return title, company

    if " at " in bio:
        before, after = bio.split(" at ", 1)
        title = before.split(",")[-1].strip().rstrip(".,") or "Unknown"
        company = after.split(",")[0].split(".")[0].strip().rstrip(".,") or "Unknown"
        return title, company

    return "Unknown", "Unknown"


def infer_seniority(title: str, bio: str) -> str:
    haystack = f"{title} {bio}".lower()
    if matches_any_keyword(haystack, _EXEC_KEYWORDS):
        return "exec"
    if matches_any_keyword(haystack, _SENIOR_KEYWORDS):
        return "senior"
    if matches_any_keyword(haystack, _JUNIOR_KEYWORDS):
        return "junior"
    return "mid"


def infer_industry(bio: str) -> str | None:
    haystack = bio.lower()
    for label, keywords in INDUSTRY_KEYWORDS:
        if matches_any_keyword(haystack, keywords):
            return label
    return None


def simulate_extraction(bio: str) -> dict:
    title, company = extract_title_company(bio)
    return {
        "title": title,
        "company": company,
        "seniority": infer_seniority(title, bio),
        "industry": infer_industry(bio),
    }


class SimulatedLLMClient(LLMClient):
    def __init__(self):
        self.model_name = "signal-simulated-llm"

    def complete(self, *, system: str, user: str) -> str:
        version = _extract_prompt_version(system)

        if version.startswith("extract"):
            bio = _extract_bio_from_user(user)
            return json.dumps(simulate_extraction(bio))

        if version.startswith("classify"):
            from app.llm.classify_simulator import simulate_classification

            profile = _extract_json_object_from_user(user)
            return json.dumps(simulate_classification(profile, prompt_version=version))

        raise ValueError(f"SimulatedLLMClient: unrecognized prompt_version {version!r}")
