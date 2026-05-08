# AGENTS.md - app/

## Package Identity
- `app/` contains the FastAPI app, API routers, business services, Celery tasks, models, config, and storage abstraction.
- Core app wiring is in `app/main.py`; domain logic is split by folder (`api`, `services`, `tasks`, `models`, `storage`).

## Setup & Run
- Start API: `uvicorn app.main:app --reload`
- Start worker: `celery -A app.tasks.celery_app worker --loglevel=info`
- Redis (local): `redis-server`
- Run app-focused tests: `pytest tests/ -v`
- Lint/format app code: `black app/ && isort app/ && flake8 app/ --max-line-length=120`

## Patterns & Conventions
- ✅ DO keep app bootstrap in `app/main.py` (router registration + middleware + lifespan only).
- ✅ DO keep shared error handlers in `app/api/exceptions.py` and register once in `app/main.py`.
- ✅ DO put request/response contracts in `app/models/schemas.py`.
- ✅ DO put shared enums in `app/models/enums.py`.
- ✅ DO load env/config via `app/config.py` (`settings` singleton).
- ✅ DO use storage abstraction from `app/storage/file_storage.py`.
- ❌ DON'T hardcode endpoint response shapes inline when a schema exists in `app/models/schemas.py`.
- ❌ DON'T put FFmpeg/Whisper/Redis heavy logic in router functions; move to `app/services/`.
- ❌ DON'T add new global mutable stores unless unavoidable; existing in-memory stores are transitional (`app/api/videos.py`, `app/api/watermarks.py`).

## Touch Points / Key Files
- App entry/lifespan/router wiring: `app/main.py`
- Global settings/env loading: `app/config.py`
- Error contracts + handler registration: `app/api/exceptions.py`
- API schemas: `app/models/schemas.py`
- Shared enums: `app/models/enums.py`
- File storage abstraction: `app/storage/file_storage.py`

## JIT Index Hints
- Find router registrations: `rg -n "app\\.include_router" app/main.py`
- Find where settings are used: `rg -n "from app\\.config import settings|settings\\." app`
- Find error codes: `rg -n "error_code|HTTPException" app/api`
- Find storage interactions: `rg -n "LocalFileStorage|get_file_path|save_" app`
- Find cross-module imports: `rg -n "from app\\.(api|services|tasks|models|storage)" app`

## Common Gotchas
- Startup validates FFmpeg + Redis in `app/main.py`; API boot may fail if either missing.
- `Settings` in `app/config.py` auto-creates storage directories at init.
- Some metadata is in-memory (`video_metadata_store`, `watermark_metadata_store`), so restarts clear it.

## Pre-PR Checks
`pytest && black --check app/ tests/ && isort --check-only app/ tests/ && flake8 app/ tests/ --max-line-length=120`
