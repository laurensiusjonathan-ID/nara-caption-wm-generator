# AGENTS.md

## Project Snapshot
- Repo type: single Python backend project (FastAPI + Celery), not a monorepo.
- Primary stack: FastAPI, Pydantic v2, Celery, Redis, FFmpeg, faster-whisper, pytest.
- Main code lives in `app/`, tests in `tests/`, runtime files in `storage/`.
- This repo uses hierarchical agent guidance: open the closest `AGENTS.md` first.
- Detailed package rules are in sub-folder AGENTS files linked below.

## Root Setup Commands
- Create venv: `python -m venv .venv`
- Activate (Windows): `.venv\Scripts\activate`
- Install deps: `pip install -r requirements.txt`
- Run API: `uvicorn app.main:app --reload`
- Run worker: `celery -A app.tasks.celery_app worker --loglevel=info`
- Run tests: `pytest`
- Check format/lint: `black --check app/ tests/ && isort --check-only app/ tests/ && flake8 app/ tests/ --max-line-length=120`
- Docker local stack: `docker-compose up -d`

## Universal Conventions
- Keep request/response contracts in `app/models/schemas.py`; avoid ad-hoc dict shapes.
- Keep enums in `app/models/enums.py`; avoid string literals scattered across modules.
- API modules orchestrate only; move processing logic to `app/services/`.
- Use `app/storage/file_storage.py` abstraction for file IO paths/placement.
- Follow formatting/lint rules from CI (`black`, `isort`, `flake8`).
- Commit style: `<Type>: <description>` (e.g., `Fix: handle missing caption file`).
- Branch naming in practice: `feature/<name>` for new work.
- Before PR: tests passing + lint clean + no debug leftovers.

## Security & Secrets
- Never commit secrets/tokens; keep env values in `.env` (local only).
- Use `.env.example` as template for required vars.
- Do not log sensitive values or full internal traces in API responses.
- Validate uploaded file types and reject unsupported formats early.

## JIT Index (what to open, not what to paste)

### Package Structure
- App architecture: `app/` -> [see app/AGENTS.md](app/AGENTS.md)
- API routes: `app/api/` -> [see app/api/AGENTS.md](app/api/AGENTS.md)
- Service/business logic: `app/services/` -> [see app/services/AGENTS.md](app/services/AGENTS.md)
- Celery tasks: `app/tasks/` -> [see app/tasks/AGENTS.md](app/tasks/AGENTS.md)
- Tests: `tests/` -> [see tests/AGENTS.md](tests/AGENTS.md)

### Quick Find Commands
- Find endpoint declarations: `rg -n "@router\.(get|post|put|delete)\(" app/api`
- Find schema models: `rg -n "^class .*\\(BaseModel\\)" app/models/schemas.py`
- Find Redis job usage: `rg -n "RedisJobManager|job_manager" app`
- Find FFmpeg processing: `rg -n "ffmpeg|subtitles|overlay" app/services`
- Find Celery task entrypoints: `rg -n "@celery_app\\.task|\\.delay\\(" app`
- Find tests for a module: `rg -n "from app\\.(api|services|tasks)" tests`

## Definition of Done
- Relevant tests pass locally (`pytest` or targeted subset).
- Formatting/lint pass (`black`, `isort`, `flake8` with CI limits).
- API behavior unchanged unless explicitly intended and covered by tests.
- No secrets committed; docs/examples updated if contract changed.
