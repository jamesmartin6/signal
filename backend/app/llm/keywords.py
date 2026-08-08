"""Shared word-boundary keyword matching for the simulator.

Plain substring checks are a real bug source here: "engineer" in
"engineering", "lead" in "leadership", "intern" in "international" all
match with naive `kw in haystack`, silently corrupting seniority/industry/
role inference. `\\b`-bounded regex avoids the whole class of false
positives while still matching multi-word phrases like "head of" or
hyphenated ones like "co-founder" (the boundary only has to hold at the
phrase's own start/end).
"""

import re


def matches_any_keyword(haystack: str, keywords: list[str]) -> bool:
    return any(re.search(rf"\b{re.escape(kw)}\b", haystack) for kw in keywords)
