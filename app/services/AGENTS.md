# AGENTS.md - app/services/

## Package Identity
- `app/services/` holds business logic and integrations: FFmpeg video/audio processing, Whisper transcription, caption formatting, and Redis job management.
- Keep this layer framework-light; API routers call into these services.

## Setup & Run
- Run service-level tests: `pytest tests/test_video_service.py tests/test_caption_generator.py tests/test_watermark_applicator.py tests/test_video_processor.py tests/test_job_manager.py tests/test_caption_formatter.py -v`
- Format services: `black app/services/`
- Sort imports: `isort app/services/`
- Lint services: `flake8 app/services/ --max-line-length=120`

## Patterns & Conventions
- ✅ DO define typed exceptions per service (`VideoProcessingError`, `CaptionGenerationError`, `WatermarkValidationError`).
- ✅ DO validate file existence/format before FFmpeg calls.
- ✅ DO separate pure formatting/parsing from IO (see `app/services/caption_formatter.py`).
- ✅ DO keep job lifecycle transitions in one place (`app/services/job_manager.py`).
- ✅ DO return deterministic output paths/formats (`app/services/video_processor.py` always MP4).
- ✅ DO keep helper constants for defaults (`DEFAULT_OPACITY`, `DEFAULT_POSITION` in `watermark_applicator.py`).
- ❌ DON'T leak low-level raw errors to API consumers; raise service exceptions and let API map them.
- ❌ DON'T duplicate timestamp validation logic; use `validate_timestamps` from `caption_formatter.py`.
- ❌ DON'T bypass `RedisJobManager` transition rules with ad-hoc Redis writes.

## Database
- Data layer here is Redis-backed for jobs, not SQL ORM.
- Redis access and key strategy live in `app/services/job_manager.py`.
- Job transition validation is enforced in `_is_valid_transition`.
- For any new job type, extend creation/listing paths in `RedisJobManager` first.

## Touch Points / Key Files
- Video metadata/validation: `app/services/video_service.py`
- Caption generation (audio + whisper): `app/services/caption_generator.py`
- Caption parsing/formatting: `app/services/caption_formatter.py`
- Watermark validation/apply: `app/services/watermark_applicator.py`
- Combined processing pipeline: `app/services/video_processor.py`
- Job persistence/lifecycle: `app/services/job_manager.py`

## JIT Index Hints
- Find FFmpeg usage: `rg -n "ffmpeg|overlay|subtitles|probe" app/services`
- Find custom exceptions: `rg -n "^class .*Error\\(Exception\\)" app/services`
- Find timestamp logic: `rg -n "timestamp|validate_timestamps|parse_srt|parse_vtt" app/services/caption_formatter.py`
- Find Redis interactions: `rg -n "redis\\.|hset|hgetall|smembers|sadd|srem" app/services/job_manager.py`
- Find output format assumptions: `rg -n "mp4|OUTPUT_FORMAT|DEFAULT_" app/services`

## Common Gotchas
- FFmpeg subtitle path escaping is platform-sensitive (`app/services/video_processor.py`).
- `transcribe_audio` loads Whisper model dynamically; runtime dependency missing will raise at call-time.
- Keep cleanup in `generate_captions` (`finally` removes temp audio).

## Pre-PR Checks
`pytest tests/test_video_service.py tests/test_caption_generator.py tests/test_watermark_applicator.py tests/test_video_processor.py tests/test_job_manager.py tests/test_caption_formatter.py -v`
