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

## Phase 2 — Extraction stage
- [ ] `backend/app/pipeline/schemas.py` — ExtractedProfile
- [ ] `backend/app/llm/client.py` — LLMClient interface, AnthropicLLMClient, SimulatedLLMClient, retry-on-validation-failure logic
- [ ] `backend/app/pipeline/prompts/extract_v1.py`
- [ ] `backend/app/pipeline/extract.py` — run_extract(), writes pipeline_stage_results row
- [ ] Unit tests: valid response, invalid-then-valid-on-retry, invalid-twice (failure path) — mocked LLM client
- [ ] Commit

## Phase 3 — Classify / Enrich / Route + orchestration
- [ ] `backend/app/pipeline/schemas.py` additions — ClassificationResult
- [ ] `backend/app/pipeline/prompts/classify_v1.py`
- [ ] `backend/app/pipeline/classify.py`
- [ ] Identify a real v1 weakness via testing/eval cases; write `classify_v2.py` fixing it
- [ ] `backend/app/pipeline/enrich.py` — deterministic mock enrichment
- [ ] `backend/app/pipeline/route.py` — pure business logic routing
- [ ] `backend/app/pipeline/runner.py` — run_pipeline(lead_id) state machine, per-stage failure handling
- [ ] Wire `run_pipeline` as BackgroundTask from POST /leads/upload
- [ ] Integration test: 3 sample leads through full pipeline, assert status + 4 stage rows each
- [ ] Commit

## Phase 4 — Evals
- [ ] `backend/app/evals/cases/classify_cases.json` — ~20 hand-labeled cases incl. edge cases
- [ ] `backend/app/evals/run_eval.py` — CLI, scores a prompt version, writes eval_runs row
- [ ] `backend/app/api/evals.py` — GET /evals
- [ ] Actually run classify_v1 and classify_v2 against the eval set; record real pass rates
- [ ] Confirm at least one case v1 fails and v2 fixes
- [ ] Put the real numbers into README (Phase 6)
- [ ] Commit

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
