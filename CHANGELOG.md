# Changelog

Semua perubahan penting pada project ini akan didokumentasikan di file ini.

Format berdasarkan [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
dan project ini mengikuti [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release

## [0.1.0] - 2025-02-01

### Added
- Video upload dan management (MP4, MOV, AVI)
- Auto caption generation dengan faster-whisper
- Dukungan bahasa Indonesia untuk caption
- Output format SRT dan VTT
- Caption editing dan retrieval
- Watermark upload (PNG dengan transparency)
- Watermark positioning (top-left, top-right, bottom-left, bottom-right, center)
- Watermark opacity configuration
- Video processing dengan burn caption dan watermark
- Background job processing dengan Celery + Redis
- Job status tracking
- RESTful API dengan FastAPI
- Auto-generated OpenAPI documentation
- Docker dan Docker Compose support
- File-based storage system

### Technical
- FastAPI untuk REST API
- Celery untuk background tasks
- Redis untuk message broker
- FFmpeg untuk video processing
- faster-whisper untuk speech-to-text
- Pydantic untuk data validation
