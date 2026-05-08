# Nara Caption & Watermark Generator

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![CI](https://github.com/laurensiusjonathan-ID/nara-caption-wm-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/laurensiusjonathan-ID/nara-caption-wm-generator/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Desktop-first pipeline untuk mempercepat produksi video e-learning: **auto-caption + watermark batch processing** dengan kualitas konsisten dan workflow yang bisa dipakai non-teknis.

---

## Why this project

Produksi konten kursus sering makan waktu karena proses repetitif:
- generate caption per video,
- burn subtitle ke output,
- tambahkan branding watermark,
- monitor proses untuk banyak file sekaligus.

Project ini dibuat untuk mengubah proses manual itu jadi **workflow yang repeatable**, terukur, dan siap dipakai tim kecil.

---

## What you can do with it

- **Batch process banyak video** (MP4/MOV/AVI) dalam satu alur.
- **Generate caption otomatis** (Indonesia/English) pakai Whisper.
- **Burn watermark** dengan posisi dan opacity yang bisa diatur.
- **Pilih mode cover**: delay overlay atau intro merge.
- **Pantau progress job** via API (Celery + Redis).
- **Jalankan lewat desktop UI** (CustomTkinter) untuk operator non-dev.

---

## Product highlights (portfolio view)

- **Business impact:** memangkas waktu handling video dari proses manual per-file jadi batch workflow.
- **Operator-friendly:** UI desktop untuk tim konten, bukan hanya API untuk engineer.
- **Production-minded:** asynchronous background jobs, structured API, dan test suite.
- **Extensible:** API-first architecture memudahkan integrasi ke frontend web/mobile di fase berikutnya.

---

## Architecture snapshot

- **Desktop UI:** CustomTkinter (`ui_batch_app/`)
- **Backend API:** FastAPI (`app/main.py`)
- **Async jobs:** Celery + Redis (`app/tasks/`)
- **Media processing:** FFmpeg (`app/services/video_processor.py`)
- **Caption engine:** faster-whisper (`app/services/caption_generator.py`)

Current mode: **desktop-first**. Karena sekarang dipakai lokal via desktop app, CORS browser tidak diaktifkan secara default.

---

## Quick start (desktop-first)

### 1) Prepare environment (Python 3.11+)

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Install FFmpeg:
- Ubuntu: `sudo apt-get install ffmpeg`
- macOS: `brew install ffmpeg`
- Windows: install dari ffmpeg.org dan pastikan masuk PATH

### 2) Start infrastructure

```bash
redis-server
```

### 3) Start API + worker

```bash
# terminal 1
uvicorn app.main:app --reload

# terminal 2
celery -A app.tasks.celery_app worker --loglevel=info
```

### 4) Launch desktop UI

```bash
batch_ui.bat
```

Atau:

```bash
python -m ui_batch_app.main
```

---

## Batch workflow

1. Pilih folder video input.
2. Tentukan output folder.
3. Pilih logo PNG (watermark mandatory).
4. Pilih caption ON/OFF + cover mode.
5. Start run dan pantau progress + summary.

Exit code batch:
- `0` semua success/skip
- `1` partial failure
- `2` fatal startup/config/preflight
- `3` tidak ada video input

---

## API endpoints (core)

| Domain | Endpoint examples |
|---|---|
| Videos | `POST /api/v1/videos/upload`, `GET /api/v1/videos/{video_id}` |
| Captions | `POST /api/v1/videos/{video_id}/captions/generate`, `GET /api/v1/videos/{video_id}/captions` |
| Watermarks | `POST /api/v1/watermarks/upload`, `GET /api/v1/watermarks/{watermark_id}` |
| Processing | `POST /api/v1/videos/{video_id}/process`, `GET /api/v1/videos/{video_id}/output` |
| Jobs | `GET /api/v1/jobs/{job_id}`, `GET /api/v1/jobs` |

Interactive docs:
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Tech stack

- Python, FastAPI, Pydantic
- Celery, Redis
- FFmpeg, faster-whisper
- CustomTkinter
- Pytest

---

## Project structure

```text
.
├── app/                # API, services, tasks
├── ui_batch_app/       # Desktop UI layer
├── scripts/            # Batch processing utilities
├── tests/              # Unit & integration tests
├── .github/workflows/  # CI pipeline
└── README.md
```

---

## Testing

```bash
pytest
pytest --cov=app
```

---

## Roadmap ideas

- Preset templates per course brand
- Multi-language caption packs
- Export analytics (durasi, failed reasons, throughput)
- Optional web dashboard on top of existing API

---

## License

MIT — lihat [LICENSE](LICENSE).
