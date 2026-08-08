"""Extraction prompt v1: bio text -> ExtractedProfile JSON."""

PROMPT_VERSION = "extract_v1"

_SCHEMA_DESCRIPTION = """{
  "title": string,               // the person's job title, as stated or clearly implied
  "company": string,              // the company name
  "seniority": "junior" | "mid" | "senior" | "exec",
  "industry": string | null       // one or two words, e.g. "fintech", "healthcare"; null if not inferable
}"""

_FEW_SHOT_EXAMPLES = [
    (
        "Jane Doe. Senior Vice President of Engineering at Acme Corp, "
        "leading a 40-person team building fintech infrastructure.",
        '{"title": "Senior Vice President of Engineering", "company": "Acme Corp", '
        '"seniority": "exec", "industry": "fintech"}',
    ),
    (
        "John Smith is a Software Engineer II at Beta Inc, working on backend "
        "distributed systems for their e-commerce platform.",
        '{"title": "Software Engineer II", "company": "Beta Inc", '
        '"seniority": "mid", "industry": "e-commerce"}',
    ),
    (
        "Maria Garcia, Marketing Intern at Delta Co.",
        '{"title": "Marketing Intern", "company": "Delta Co", '
        '"seniority": "junior", "industry": null}',
    ),
    (
        "Dr. Alex Chen, Chief Technology Officer and co-founder of NovaHealth, "
        "a healthcare technology startup.",
        '{"title": "Chief Technology Officer", "company": "NovaHealth", '
        '"seniority": "exec", "industry": "healthcare"}',
    ),
]


def build_prompt(raw_input: dict) -> tuple[str, str]:
    examples_text = "\n\n".join(
        f'Bio:\n"""\n{bio}\n"""\nJSON: {json_out}' for bio, json_out in _FEW_SHOT_EXAMPLES
    )

    system = f"""[prompt_version={PROMPT_VERSION}]
You are a data extraction engine. Given a short bio or professional
description, extract a structured profile matching exactly this JSON shape:

{_SCHEMA_DESCRIPTION}

Rules:
- Output ONLY the JSON object. No prose, no markdown code fence, no explanation.
- "seniority" must be exactly one of: junior, mid, senior, exec.
- If the industry cannot be reasonably inferred, use null (not a guess).

Examples:

{examples_text}"""

    name = raw_input.get("name", "")
    company_hint = raw_input.get("company", "")
    bio = raw_input.get("bio_or_linkedin_url", "")

    user = f"""Name: {name}
Company (from source list, may be incomplete): {company_hint}
Bio:
\"\"\"
{bio}
\"\"\"

Extract the structured profile as JSON."""

    return system, user
