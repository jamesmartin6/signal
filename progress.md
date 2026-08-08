# Signal — Build Progress

This file is the single source of truth for where this build stands. If you are
picking this up in a new session (context reset, usage-limit reset, etc.),
**read this file top to bottom, then run `git log --oneline -20` to see the
last few commits, then resume at the first unchecked box.**

Do not re-ask the user anything — all open decisions below are already
resolved. Keep committing after every completed checklist item (small,
working commits, not one giant commit at the end).

---

## Locked-in decisions (do not revisit)

- **LLM provider:** Anthropic Claude, via the official `anthropic` Python SDK.
  There is no `ANTHROPIC_API_KEY` (or any LLM key) available in this dev
  environment. Solution: `app/llm/client.py` defines an `LLMClient`
  interface with two implementations —
  - `AnthropicLLMClient` (real API calls, used when `ANTHROPIC_API_KEY` is set)
  - `SimulatedLLMClient` (deterministic, rule-based stand-in that mimics the
    same input→structured-output contract, including a realistic,
    reproducible weakness in `classify_v1` that `classify_v2` fixes)
  `get_llm_client()` picks whichever is appropriate based on env. This keeps
  the whole pipeline + eval suite runnable with zero config (important for
  "a stranger clones the repo" in Phase 6's definition of done) while still
  being a real, swappable integration for anyone who adds a key. Document
  this honestly and prominently in the README — do not overstate it as
  "real LLM calls" when a key isn't present.
- **Database:** SQLAlchemy 2.0 models using the generic `sqlalchemy.JSON`
  column type (not Postgres-only `JSONB`) so the exact same models work
  against SQLite (zero-config local dev/tests) and Postgres (docker-compose
  stack, matches build-plan spec). `DATABASE_URL` env var selects the
  backend; defaults to a local SQLite file if unset.
- **No Docker available in this sandbox** (`docker` CLI not installed). A
  correct `docker-compose.yml` (Postgres + backend + frontend) is still
  written per spec for anyone who has Docker, but verification in this
  session is done via local venv (backend) + local `npm run dev`/`build`
  (frontend) + SQLite. Call this out plainly in the README rather than
  claiming `docker compose up` was tested.
- **Python packaging:** plain `venv` + `pip` + `pyproject.toml`. No
  poetry/uv available. **Do not use the `python` on PATH in git-bash** — it
  resolves to msys2's `C:/msys64/ucrt64/bin/python.exe`, which reports
  platform tag `mingw_x86_64_ucrt_gnu`. PyPI has no wheels for that ABI, so
  installing anything with compiled deps (pydantic-core, jiter, etc.) tries
  to build from source and fails without a Rust toolchain. Instead use the
  standard CPython already installed at
  `C:\Users\James\AppData\Local\Programs\Python312-taskflow\python.exe`
  (platform tag `win-amd64`, leftover from an earlier unrelated project on
  this machine, reused here rather than installing a duplicate) to create
  `backend/.venv`. That venv uses the normal Windows layout —
  `backend/.venv/Scripts/python.exe`, not `bin/`.
- **Background jobs:** FastAPI `BackgroundTasks`, per spec (no Celery/Redis).
- **Frontend:** Vite + React + TypeScript, plain CSS (no UI framework),
  polling via `setInterval`, no WebSockets.
- **Git:** commits authored by the user (jamesmartin6), no AI co-author
  trailers. `includeCoAuthoredBy` is already `false` in global Claude Code
  settings.
- **The original planning doc** `signal-build-plan.md` stays local only
  (gitignored) — not published in the public repo, to keep the repo's
  homepage/README as the single clean entry point.

---

## Phase 0 — Repo scaffold
- [x] `git init -b main`
- [x] Directory skeleton created
- [x] `.gitignore`
- [x] `progress.md` (this file)
- [ ] Initial commit

## Phase 1 — Backend skeleton & data layer — DONE
- [x] `backend/pyproject.toml` with deps (fastapi, uvicorn, sqlalchemy, alembic, pydantic v2, anthropic, python-multipart, psycopg (optional, for postgres), pytest, httpx)
- [x] `backend/app/config.py` — Settings (DATABASE_URL, ANTHROPIC_API_KEY, etc.)
- [x] `backend/app/db/models.py` — Lead, PipelineStageResult, EvalRun (+ `seq` monotonic counter column — see note below)
- [x] `backend/app/db/session.py` — engine/session
- [x] `backend/app/main.py` — FastAPI app, `/health`, CORS for frontend dev
- [x] Alembic init + initial migration for the 3 tables
- [x] `backend/app/api/leads.py` — POST /leads/upload, GET /leads, GET /leads/{id}
- [x] CSV parsing logic (`app/ingest.py`) + unit tests (malformed rows, missing columns, empty file, header-only, ragged rows, blank lines)
- [x] Manual verification: ran uvicorn locally, curl upload (3 created/1 skipped) + list + detail + 404 — all correct
- [x] Commit

**Bug caught during manual verification (real, not hypothetical):** all leads
created in one upload batch got the *exact same* `created_at` timestamp
(confirmed live: `"2026-08-08T22:06:42.114194"` on all 3 rows). Sorting
`GET /leads` by `created_at` would have tie-broken on random UUID, scrambling
upload order in the UI. Fixed by adding `Lead.seq`, a process-local monotonic
counter (`itertools.count`, reseeded from `MAX(seq)` in the DB at app
startup in `main.py`'s lifespan so restarts against a persisted DB never
hand out colliding values). `GET /leads` now orders by `seq` only.

Env quirk hit and resolved: git-bash's `curl.exe -F file=@/c/path/...`
silently fails (exit 26) because MSYS's path-mangling doesn't rewrite paths
embedded after `@` inside a larger arg — use a `cygpath -w` converted
Windows-style path for any future curl file-upload testing.

## Phase 2 — Extraction stage — DONE
- [x] `backend/app/pipeline/schemas.py` — ExtractedProfile (+ ClassificationResult stub for Phase 3)
- [x] `backend/app/llm/client.py` — LLMClient interface, AnthropicLLMClient, retry-on-validation-failure logic (`generate_structured`)
- [x] `backend/app/llm/simulator.py` — SimulatedLLMClient, the zero-config fallback (see Locked-in decisions). Extraction heuristics: regex title/company split (`is a/an X at Y` and `, X at Y` patterns), keyword-based seniority + industry inference.
- [x] `backend/app/pipeline/prompts/extract_v1.py` — few-shot prompt, `[prompt_version=...]` marker convention (lets the simulator dispatch on which stage/version a prompt is for without a separate out-of-band signal)
- [x] `backend/app/pipeline/extract.py` — run_extract(), writes pipeline_stage_results row, advances lead.status extracting→classifying (or →failed)
- [x] Unit tests (`tests/test_extract.py`, `tests/fakes.py::FakeLLMClient`): valid response, invalid-then-valid-on-retry, invalid-twice (failure path)
- [x] `tests/test_llm_simulator.py` — heuristic unit tests
- [x] `tests/test_extract_e2e_simulated.py` — real (non-mocked) run through 5 sample bios, checks Phase 2's "≥4/5 without retry" bar (met: 5/5, since the simulator is schema-safe by construction — the real signal is the per-bio seniority/industry assertions)
- [x] `tests/test_extract_real_api.py` — opt-in real Anthropic API integration test, skipped unless `RUN_REAL_LLM_TESTS=1` and `ANTHROPIC_API_KEY` are both set
- [x] Commit

**Bug caught during testing:** the simulator's industry keyword list had
`"media"` and `"marketing"` as generic industry keywords, which
false-matched job-function phrasing ("Marketing Intern", "social media
campaigns") that says nothing about the employer's actual industry. Fixed
by requiring more specific compound phrases (`"marketing agency"`,
`"advertising agency"`, `"entertainment"`, `"streaming"`, etc.) instead of
bare `"media"`/`"marketing"`.

## Phase 3 — Classify / Enrich / Route + orchestration — DONE
- [x] `backend/app/pipeline/schemas.py` additions — ClassificationResult, EnrichmentResult, RouteResult
- [x] `backend/app/pipeline/prompts/classify_v1.py` / `classify_v2.py` — real v1 weakness: v1's prompt says "senior/exec-level roles" are decision makers without distinguishing role function from seniority, so a "Principal Software Engineer" (senior IC, no purchasing authority) gets misclassified as decision_maker. v2 explicitly checks function (technical keywords) before seniority, with a few-shot example for exactly this case.
- [x] `backend/app/llm/classify_simulator.py` — mirrors the same v1/v2 logic difference for the zero-config simulated path, so the offline demo tells the same honest story as the real-LLM path
- [x] `backend/app/pipeline/classify.py` — run_classify() + pure `classify_profile()` (no DB) for eval-harness reuse
- [x] `backend/app/pipeline/enrich.py` — no LLM; deterministic rules: slugified company domain, hash-bucketed company size, industry lookup-fallback when extraction left it null
- [x] `backend/app/pipeline/route.py` — pure business logic; confidence < 0.6 always -> needs_review
- [x] `backend/app/pipeline/runner.py` — run_pipeline(lead_id): extract->classify->enrich->route, catches PipelineStageFailed (stage already recorded it) and any unexpected exception (marks lead failed) so one bad lead can't crash a batch
- [x] Wired `run_pipeline_background` as a BackgroundTask from POST /leads/upload (deferred import in leads.py, added back in Phase 1 in anticipation of this)
- [x] `tests/test_pipeline_e2e.py` — 3 leads through the full real (simulated) pipeline, asserts status=done + exactly 4 stage rows each in order
- [x] `tests/test_classify.py`, `tests/test_enrich.py`, `tests/test_route.py`, `tests/test_classify_simulator.py`
- [x] Commit

**Two real bugs caught during Phase 3 testing:**

1. **Word-boundary keyword matching.** The simulator's keyword lists used
   plain substring checks (`kw in haystack`), which silently broke on
   real inputs: `"engineer"` matched inside `"Engineering"` (so "VP of
   **Engineering**" was misclassified as `technical`, not
   `decision_maker` — caught by
   `test_both_versions_agree_on_unambiguous_decision_maker`), and the same
   class of bug would have hit `"lead"` inside `"leadership"` and
   `"intern"` inside `"international"`. Fixed with a shared
   `app/llm/keywords.py::matches_any_keyword()` using `\b`-bounded regex,
   applied to every keyword list in `simulator.py` and
   `classify_simulator.py`.
2. **Test DB architecture.** Once `runner.py` existed, `POST
   /leads/upload`'s background task started actually running — and
   FastAPI's BackgroundTasks execute inside `TestClient` synchronously,
   before the HTTP response returns, on a session opened from the app's
   *global* `SessionLocal`/`engine`. The old test setup used
   `sqlite:///:memory:` for that global engine while `db_session`/`client`
   fixtures pointed a *separate* in-memory DB (via dependency override) at
   the request layer — two different, unconnected in-memory databases.
   The background task's session saw an empty, table-less DB:
   `OperationalError: no such table: leads`. Fixed by pointing
   `DATABASE_URL` at a shared temp **file** for the whole test session
   (see `tests/conftest.py`) so every session/thread reads and writes the
   same real database, matching how SQLite/Postgres actually behave in
   production. This also means `test_leads_api.py`'s assertions changed
   from Phase 1 (`status == "pending"`, empty trace) to Phase 3 reality
   (`status == "done"`, full 4-stage trace) since the pipeline now runs to
   completion inline during the test's `client.post(...)` call.

Manual end-to-end verification via curl (4 leads: a CMO, a Data Engineer, a
Principal Software Engineer, and a Marketing Intern) confirmed all reach
`done` with correct routing, and specifically confirmed the
Principal-Software-Engineer trace classifies as `technical` under
`classify_v2` (the pipeline's default) — the exact case classify_v1 gets
wrong.

## Phase 4 — Evals — DONE
- [x] `backend/app/evals/cases/classify_cases.json` — 22 hand-labeled cases (7 decision_maker, 6 technical, 6 not_relevant... see file; includes 3 senior-IC edge cases + 2 deliberately ambiguous cases with `notes` fields explaining the judgment call)
- [x] `backend/app/evals/run_eval.py` — CLI (`python -m app.evals.run_eval --prompt-version classify_v1|v2`), scores via the pure `extract_profile`/`classify_profile` functions (no DB writes except the final EvalRun row), prints pass/fail detail, writes eval_runs row
- [x] `backend/app/api/evals.py` — GET /evals (already anticipated by a try/except ImportError in main.py back in Phase 1)
- [x] `tests/test_run_eval.py`, `tests/test_evals_api.py`
- [x] Actually ran both prompt versions against the (simulated-path) eval set — see real numbers below
- [x] Confirmed: v1 fails all 3 senior-IC edge cases (Principal/Staff/Distinguished Engineer), v2 fixes all 3
- [x] Commit

### Real eval numbers (simulated-LLM path — no ANTHROPIC_API_KEY in this environment)

```
classify_v1: 19/22 passed (86.4%)
classify_v2: 22/22 passed (100.0%)
```

classify_v1's 3 failures were all the same root cause: `"Seniority 'senior'
treated as decision-making authority (v1 logic)"` — Principal/Staff/
Distinguished Engineer, all senior-sounding IC titles, misclassified as
`decision_maker`. classify_v2 fixed all 3 by checking role function before
seniority. These numbers go straight into the README (Phase 6) as the
project's headline "before/after" metric.

Note for anyone who later adds a real `ANTHROPIC_API_KEY`: re-run both
`python -m app.evals.run_eval --prompt-version classify_v1` and `...v2` —
the real-LLM numbers will likely differ from the simulated ones above
(a real model may handle some of the not_relevant/ambiguous cases
differently) and should replace them in the README if so, with an honest
note about which path (simulated vs. real) produced which numbers.

## Phase 5 — Frontend
- [ ] Vite + React + TS scaffold (`npm create vite`)
- [ ] `frontend/src/types/lead.ts` mirroring backend schemas
- [ ] `frontend/src/api/client.ts` typed fetch wrapper
- [ ] `UploadForm.tsx`
- [ ] `useLeadsPolling.ts` + `LeadsTable.tsx`
- [ ] `LeadTrace.tsx`
- [ ] `EvalDashboard.tsx`
- [ ] `App.tsx` wiring + minimal CSS
- [ ] `npm run build` passes (tsc + vite build)
- [ ] End-to-end manual check against running backend (curl-level + served bundle)
- [ ] Commit

## Phase 6 — Logging, docs, polish
- [ ] `backend/app/logging_config.py` — structured logs per pipeline stage call
- [ ] `docker-compose.yml` — postgres + backend + frontend
- [ ] Backend `Dockerfile`, frontend `Dockerfile`
- [ ] `README.md` — architecture, quickstart (no-Docker path + Docker path), real eval numbers, screenshots/notes
- [ ] Final full-repo sanity pass (fresh venv install + test run)
- [ ] Commit

## Publish
- [ ] `gh repo create` (public, good description)
- [ ] Push main
- [ ] Verify README renders well on GitHub, repo has topics/description set
- [ ] Final check of progress.md — mark everything done

---

## Session log

- **2026-08-08**: Session started. Environment survey: no Docker, no
  ANTHROPIC_API_KEY/OPENAI_API_KEY, Python 3.14 (msys2, venv uses `bin/`),
  Node v22.14/npm 10.9.2, `gh` authenticated as jamesmartin6, git identity
  already configured. Decisions above locked in. Starting Phase 1.
