"""Classification prompt v1: ExtractedProfile -> ClassificationResult JSON.

Known weakness (kept intentionally, fixed in classify_v2.py): this prompt
tells the model to treat "senior/exec-level roles" as decision makers
without distinguishing role *function* from role *seniority*. A senior or
principal-level individual contributor (e.g. "Principal Software Engineer")
has a senior-sounding title but no purchasing authority — v1 tends to
misclassify these as decision_maker. See classify_v2.py for the fix and
evals/cases/classify_cases.json for the case that catches it.
"""

from app.pipeline.schemas import ExtractedProfile

PROMPT_VERSION = "classify_v1"

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
]


def build_prompt(profile: ExtractedProfile) -> tuple[str, str]:
    examples_text = "\n\n".join(
        f"Profile: {profile_dict}\nJSON: {json_out}" for profile_dict, json_out in _FEW_SHOT_EXAMPLES
    )

    system = f"""[prompt_version={PROMPT_VERSION}]
You are a lead-qualification engine for a B2B developer-tools company. Given
a structured profile, classify the person into exactly one category:

{_SCHEMA_DESCRIPTION}

Rules:
- "decision_maker": senior or exec-level roles — VPs, Directors, C-suite, Founders — who hold budget or purchasing authority.
- "technical": hands-on engineering/technical roles.
- "not_relevant": everyone else (sales, marketing, interns, unrelated functions).
- Output ONLY the JSON object. No prose, no markdown fence.

Examples:

{examples_text}"""

    user = f"Extracted profile:\n{profile.model_dump_json()}\n\nClassify this lead as JSON."
    return system, user
