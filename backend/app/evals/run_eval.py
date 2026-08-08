"""Score a classify prompt version against the hand-labeled eval set.

Usage:
    python -m app.evals.run_eval --prompt-version classify_v2

Runs classification (via extract -> classify, using whatever LLMClient
get_llm_client() resolves to — real Anthropic if ANTHROPIC_API_KEY is set,
otherwise the deterministic simulator) against every case in
evals/cases/classify_cases.json, compares the predicted category to the
hand-labeled expected category, prints a pass-rate summary, and writes one
row to the eval_runs table so GET /evals (and the frontend dashboard) can
chart prompt-version-over-version accuracy.
"""

import argparse
import json
from pathlib import Path

from app.db.models import EvalRun, PipelineStage
from app.db.session import SessionLocal
from app.llm.client import LLMOutputInvalidError, get_llm_client
from app.pipeline.classify import classify_profile
from app.pipeline.extract import extract_profile

CASES_PATH = Path(__file__).parent / "cases" / "classify_cases.json"


def load_cases() -> list[dict]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def run_eval(prompt_version: str, *, verbose: bool = True) -> dict:
    client = get_llm_client()
    cases = load_cases()
    total = len(cases)
    passed = 0
    details = []

    for case in cases:
        raw_input = {"name": "", "company": "", "bio_or_linkedin_url": case["bio"]}
        try:
            extract_result = extract_profile(client, raw_input)
            classify_result = classify_profile(client, extract_result.output, prompt_version)
            predicted = classify_result.output.category
            reasoning = classify_result.output.reasoning
        except LLMOutputInvalidError as exc:
            predicted = None
            reasoning = f"LLM output invalid after retry: {exc}"

        is_pass = predicted == case["expected_category"]
        passed += int(is_pass)
        details.append(
            {
                "bio": case["bio"],
                "expected": case["expected_category"],
                "predicted": predicted,
                "passed": is_pass,
                "reasoning": reasoning,
            }
        )

    pass_rate = passed / total if total else 0.0

    if verbose:
        print(f"Prompt version: {prompt_version}  (model: {client.model_name})")
        print(f"Passed: {passed}/{total} ({pass_rate:.1%})\n")
        failures = [d for d in details if not d["passed"]]
        if failures:
            print("Failures:")
            for f in failures:
                print(f"  expected={f['expected']!r} predicted={f['predicted']!r}")
                print(f"    bio: {f['bio']}")
                print(f"    reasoning: {f['reasoning']}")
        else:
            print("No failures.")

    db = SessionLocal()
    try:
        db.add(
            EvalRun(
                prompt_version=prompt_version,
                stage=PipelineStage.classify,
                total_cases=total,
                passed_cases=passed,
                pass_rate=pass_rate,
            )
        )
        db.commit()
    finally:
        db.close()

    return {
        "prompt_version": prompt_version,
        "model": client.model_name,
        "total_cases": total,
        "passed_cases": passed,
        "pass_rate": pass_rate,
        "details": details,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Score a classify prompt version against the eval set.")
    parser.add_argument("--prompt-version", required=True, choices=["classify_v1", "classify_v2"])
    args = parser.parse_args()
    run_eval(args.prompt_version)


if __name__ == "__main__":
    main()
