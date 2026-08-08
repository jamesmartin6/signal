"""Classification prompt v2 — fixes a real weakness found in classify_v1.

v1 told the model that "senior/exec-level roles" are decision makers, which
conflates seniority with role *function*. A "Principal Software Engineer" or
"Staff Engineer" is senior/exec-level by seniority but is an individual
contributor with no purchasing authority — v1 misclassified these as
decision_maker. v2 makes the function check happen first: technical
keywords in the title win regardless of seniority, and only non-technical
senior/exec roles are decision_maker. One few-shot example targets exactly
this case.
"""

from app.pipeline.schemas import ExtractedProfile

PROMPT_VERSION = "classify_v2"

_SCHEMA_DESCRIPTION = """{
  "category": "decision_maker" | "technical" | "not_relevant",
  "confidence": float,   // 0.0 to 1.0
  "reasoning": string    // one sentence
}"""

_FEW_SHOT_EXAMPLES = [
    (
        {"title": "VP of Engineering", "company": "Acme Corp", "seniority": "exec", "industry": "fintech"},
        '{"category": "decision_maker", "confidence": 0.95, '
        '"reasoning": "VP-level title implies budget and purchasing authority."}',
    ),
    (
        {"title": "Marketing Intern", "company": "Delta Co", "seniority": "junior", "industry": None},
        '{"category": "not_relevant", "confidence": 0.9, '
        '"reasoning": "Junior marketing role with no technical or purchasing authority."}',
    ),
    (
        {"title": "Software Engineer", "company": "Beta Inc", "seniority": "mid", "industry": "e-commerce"},
        '{"category": "technical", "confidence": 0.85, '
        '"reasoning": "Hands-on engineering role, mid-level."}',
    ),
    (
        {"title": "Principal Software Engineer", "company": "Gamma Systems", "seniority": "senior", "industry": "saas"},
        '{"category": "technical", "confidence": 0.85, '
        '"reasoning": "Senior-level title, but the function is a hands-on engineering IC role, '
        'not a budget-holding decision maker."}',
    ),
]


def build_prompt(profile: ExtractedProfile) -> tuple[str, str]:
    examples_text = "\n\n".join(
        f"Profile: {profile_dict}\nJSON: {json_out}" for profile_dict, json_out in _FEW_SHOT_EXAMPLES
    )

    system = f"""[prompt_version={PROMPT_VERSION}]
You are a lead-qualification engine for a B2B developer-tools company. Given
a structured profile, classify the person into exactly one category:

{_SCHEMA_DESCRIPTION}

Rules (check in this order):
1. First check the role's FUNCTION, not its seniority. If the title is a
   hands-on engineering/technical role (engineer, architect, data
   scientist, DevOps/SRE, developer) — including "Principal", "Staff", or
   "Distinguished" level ICs — classify as "technical" regardless of how
   senior it sounds. Seniority alone does not imply purchasing authority.
2. Otherwise, if the role is senior or exec-level (VP, Director, C-suite,
   Founder, Head of X) with budget or purchasing authority, classify as
   "decision_maker".
3. Otherwise, classify as "not_relevant" (sales, marketing, interns,
   unrelated functions).
- Output ONLY the JSON object. No prose, no markdown fence.

Examples:

{examples_text}"""

    user = f"Extracted profile:\n{profile.model_dump_json()}\n\nClassify this lead as JSON."
    return system, user
