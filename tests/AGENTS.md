# AGENTS.md - tests/

## Package Identity
- `tests/` contains unit and API tests for all major modules: API routes, services, storage, schemas, enums, and Celery task orchestration.
- Test philosophy here: isolate external systems with mocks while validating contract behavior.

## Setup & Run
- Run all tests: `pytest`
- Run with coverage: `pytest --cov=app --cov-report=term-missing`
- Run one test file: `pytest tests/test_processing_api.py -v`
- Run one test case: `pytest tests/test_processing_api.py::TestProcessVideoEndpoint::test_process_video_not_found -v`

## Patterns & Conventions
- ✅ DO mirror module structure with `test_<module>.py` (e.g., `app/services/video_service.py` -> `tests/test_video_service.py`).
- ✅ DO use `unittest.mock.patch` for Redis/FFmpeg/Celery boundaries.
- ✅ DO test HTTP `status_code` + structured `error_code` for API failures.
- ✅ DO clean mutable stores via fixtures when tests touch in-memory metadata.
- ✅ DO assert queue/task call args for async orchestration (`tests/test_processing_api.py`, `tests/test_celery_tasks.py`).
- ❌ DON'T mutate global app/router state inside shared app objects for new tests.
- ❌ DON'T copy pattern from `tests/test_videos_api.py:21` (`app.include_router(...)` on imported global app); prefer local test app pattern from `tests/test_processing_api.py:22`.
- ❌ DON'T rely on real Redis/FFmpeg in unit tests unless explicitly writing integration tests.

## Testing
- API tests: `tests/test_videos_api.py`, `tests/test_captions_api.py`, `tests/test_watermarks_api.py`, `tests/test_processing_api.py`, `tests/test_jobs_api.py`
- Service tests: `tests/test_video_service.py`, `tests/test_caption_generator.py`, `tests/test_watermark_applicator.py`, `tests/test_video_processor.py`, `tests/test_job_manager.py`, `tests/test_caption_formatter.py`
- Core wiring/errors: `tests/test_main.py`, `tests/test_exceptions.py`
- Model checks: `tests/test_schemas.py`, `tests/test_enums.py`

## Touch Points / Key Files
- API behavior regression: `tests/test_processing_api.py`
- Background task behavior: `tests/test_celery_tasks.py`
- Storage behavior: `tests/test_file_storage.py`
- Job manager lifecycle: `tests/test_job_manager.py`
- Caption parse/format logic: `tests/test_caption_formatter.py`

## JIT Index Hints
- Find tests by module name: `rg -n "from app\\.(api|services|tasks|storage|models)" tests`
- Find endpoint assertions: `rg -n "status_code|error_code|client\\.(get|post|put|delete)" tests`
- Find fixtures cleanup patterns: `rg -n "@pytest\\.fixture|yield|clear\\(" tests`
- Find Celery apply/delay checks: `rg -n "\\.apply\\(|\\.delay\\(|call_args" tests`
- Find validation-error coverage: `rg -n "422|VALIDATION_ERROR|INVALID_" tests`

## Common Gotchas
- Shared in-memory stores (`video_metadata_store`, `watermark_metadata_store`) require cleanup to avoid cross-test pollution.
- Mock path must match import location used by target module (`app.api.processing.file_storage`, not source definition).
- Time fields may be timezone-aware; compare values carefully.

## Pre-PR Checks
`pytest && pytest --cov=app --cov-report=term-missing`
