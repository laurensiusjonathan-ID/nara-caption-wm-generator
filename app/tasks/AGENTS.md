# AGENTS.md - app/tasks/

## Package Identity
- `app/tasks/` defines Celery app configuration and background task entrypoints for caption generation, watermarking, and combined processing.
- Tasks are orchestration units: update job status, call services, handle retries/failures.

## Setup & Run
- Start worker: `celery -A app.tasks.celery_app worker --loglevel=info`
- Run task tests: `pytest tests/test_celery_tasks.py -v`
- Lint tasks package: `black app/tasks/ && isort app/tasks/ && flake8 app/tasks/ --max-line-length=120`

## Patterns & Conventions
- ✅ DO derive tasks from `BaseVideoTask` for shared retry/failure behavior (`app/tasks/video_tasks.py`).
- ✅ DO update job status progressively (`pending -> processing -> completed/failed`) using `RedisJobManager`.
- ✅ DO map retryable vs non-retryable errors explicitly (see all three task functions).
- ✅ DO keep Celery config centralized in `app/tasks/celery_app.py`.
- ✅ DO keep queue routing explicit (`captions`, `watermarks`, `processing`) in task routes.
- ❌ DON'T perform API-specific validation in tasks; that belongs in `app/api/*`.
- ❌ DON'T skip terminal status update on exceptions.
- ❌ DON'T create new task names without adding routing and tests.

## API/Worker Touch Points
- Celery app and global config: `app/tasks/celery_app.py`
- Caption task: `generate_captions_task` in `app/tasks/video_tasks.py`
- Watermark task: `apply_watermark_task` in `app/tasks/video_tasks.py`
- Combined processing task: `process_video_task` in `app/tasks/video_tasks.py`
- Job lifecycle dependency: `app/services/job_manager.py`

## JIT Index Hints
- Find task decorators: `rg -n "@celery_app\\.task" app/tasks`
- Find status updates: `rg -n "update_status\\(" app/tasks/video_tasks.py`
- Find retry logic: `rg -n "retry|max_retries|MaxRetriesExceededError|autoretry_for" app/tasks`
- Find queue routes: `rg -n "task_routes|task_default_queue" app/tasks/celery_app.py`
- Find service calls per task: `rg -n "generate_captions|apply_watermark|process_video" app/tasks/video_tasks.py`

## Common Gotchas
- `job_id` extraction in `on_failure` supports kwargs and args; keep signature compatibility.
- Invalid enum conversion (`CaptionFormat`, `WatermarkPosition`) will throw; ensure API sends validated values.
- Avoid import-time Redis side effects; `job_manager` is lazy-loaded in base task.

## Pre-PR Checks
`pytest tests/test_celery_tasks.py -v`
