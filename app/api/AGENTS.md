# AGENTS.md - app/api/

## Package Identity
- `app/api/` defines HTTP endpoints and request orchestration for videos, captions, watermarks, processing, and jobs.
- Routers translate HTTP input/output; service layer executes core business logic.

## Setup & Run
- Run API locally: `uvicorn app.main:app --reload`
- Run API-focused tests: `pytest tests/test_*api.py -v`
- Single module tests: `pytest tests/test_processing_api.py -v`
- Lint api package: `black app/api/ && isort app/api/ && flake8 app/api/ --max-line-length=120`

## Patterns & Conventions
- ✅ DO declare endpoints with explicit `response_model` (see `app/api/processing.py`, `app/api/captions.py`).
- ✅ DO return standardized error payloads with `error_code/message/details` (see `app/api/videos.py`).
- ✅ DO validate existence/inputs early before queuing tasks (see `app/api/processing.py`).
- ✅ DO use models from `app/models/schemas.py` and enums from `app/models/enums.py`.
- ✅ DO queue background work via `.delay(...)` from `app/tasks/video_tasks.py`.
- ✅ DO use `LocalFileStorage` to resolve paths before processing.
- ❌ DON'T embed FFmpeg or Whisper processing directly in router handlers.
- ❌ DON'T bypass schema models with ad-hoc response dicts when schema already exists.
- ❌ DON'T duplicate exception handling logic per endpoint; centralize in `app/api/exceptions.py`.

## API Patterns
- REST routes live in `app/api/*.py` and are mounted in `app/main.py`.
- Validation + defaults should rely on Pydantic models (`ProcessVideoRequest`, `CaptionGenerateRequest`).
- Job orchestration pattern: create job via `RedisJobManager` then queue Celery task (`app/api/processing.py`).
- 404 contract examples:
  - Video not found: `app/api/videos.py`
  - Watermark not found: `app/api/watermarks.py`
  - Job not found: `app/api/jobs.py`

## Touch Points / Key Files
- Video endpoints: `app/api/videos.py`
- Caption endpoints: `app/api/captions.py`
- Watermark endpoints: `app/api/watermarks.py`
- Processing endpoints: `app/api/processing.py`
- Job endpoints: `app/api/jobs.py`
- Exception handlers: `app/api/exceptions.py`

## JIT Index Hints
- Find all route handlers: `rg -n "@router\\.(get|post|put|delete)\\(" app/api`
- Find where background jobs are queued: `rg -n "\\.delay\\(" app/api`
- Find error responses: `rg -n "HTTPException\\(|error_code" app/api`
- Find in-memory metadata usage: `rg -n "video_metadata_store|watermark_metadata_store" app/api`
- Find schema usage by endpoint: `rg -n "response_model=|Request|Response" app/api`

## Common Gotchas
- `ProcessVideoRequest` requires at least one operation (`apply_captions` or `apply_watermark`) in endpoint logic.
- Caption retrieval auto-converts between SRT/VTT when source format differs (`app/api/captions.py`).
- Existing metadata stores are process-memory; not durable across restart.

## Pre-PR Checks
`pytest tests/test_videos_api.py tests/test_captions_api.py tests/test_watermarks_api.py tests/test_processing_api.py tests/test_jobs_api.py -v`
