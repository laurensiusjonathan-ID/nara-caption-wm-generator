# Video Caption Watermark API

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

API untuk menambahkan caption otomatis dan watermark ke video e-course. Dibangun dengan FastAPI, Celery, dan FFmpeg. Mendukung bahasa Indonesia untuk caption generation menggunakan faster-whisper.

> Mode saat ini: **desktop-first (CustomTkinter)**. Backend dijalankan untuk dipakai UI desktop lokal, sehingga CORS browser tidak diaktifkan secara default.

## ✨ Fitur

- 🎥 **Upload & Manajemen Video** - Support MP4, MOV, AVI
- 📝 **Auto Caption Generation** - Speech-to-text dengan dukungan Bahasa Indonesia
- 🖼️ **Watermark** - Tambahkan logo dengan posisi dan opacity yang bisa dikustomisasi
- ⚙️ **Background Processing** - Async job dengan Celery + Redis
- 📊 **Job Tracking** - Monitor status dan progress processing
- 🐳 **Docker Ready** - Deploy mudah dengan Docker Compose
- 📚 **API Docs** - Auto-generated OpenAPI/Swagger

## 🚀 Quick Start

### Menggunakan Docker Compose (Recommended)

```bash
# Clone repo
git clone https://github.com/username/video-caption-watermark-api.git
cd video-caption-watermark-api

# Copy environment file
cp .env.example .env

# Start services
docker-compose up -d

# Cek status
docker-compose ps
```

Akses API:
- 🌐 API: http://localhost:8000
- 📖 Swagger UI: http://localhost:8000/docs
- 📘 ReDoc: http://localhost:8000/redoc

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Install FFmpeg
# Ubuntu: sudo apt-get install ffmpeg
# macOS: brew install ffmpeg
# Windows: download dari ffmpeg.org

# Start Redis
redis-server

# Start API (terminal 1)
uvicorn app.main:app --reload

# Start Celery worker (terminal 2)
celery -A app.tasks.celery_app worker --loglevel=info
```

## 🎬 Batch Script Usage (Many Videos + 1 Logo)

Untuk proses banyak video otomatis via Windows script:

### 1) Siapkan input folder

Masukkan file ke `storage/batch_input/`:
- banyak video (`.mp4`, `.mov`, `.avi`)
- **tepat 1** file logo `.png`

Contoh:

```text
storage/batch_input/
├── kelas-01.mp4
├── kelas-02.mov
├── kelas-03.avi
└── logo.png
```

Rule logo:
- 0 logo PNG -> batch berhenti (fatal)
- >1 logo PNG -> batch berhenti (fatal)

### 2) Jalankan batch

Mode CLI (existing):

```bat
batch_process.bat
```

Mode UI (CustomTkinter) — **utama/recommended**:

```bat
batch_ui.bat
```

Atau smoke run langsung:

```bash
python -m ui_batch_app.main
```

Catatan:
- `test-ui.html` hanya untuk pengujian manual berbasis browser.
- Karena mode default desktop-only, CORS backend tidak diaktifkan secara default.

> Launcher `.bat` **wajib virtual environment** (`.venv` atau `venv`).  
> Jika tidak ditemukan, script akan stop dengan error dan tidak lanjut proses.

Behavior rules:
1. Watermark selalu ON (mandatory)
2. Caption optional (OFF = skip generate + burn caption)
3. Cover mode exclusive: `delay_overlay` atau `intro_merge`
4. `intro_merge` dieksekusi terakhir: main video diproses dulu, lalu intro plain di-prepend
5. Intro tetap plain (tanpa caption/watermark)
6. Simpan hasil ke output folder yang dipilih/di-config

### 3) Cek output

Hasil akhir ada di:

```text
storage/batch_output/
├── kelas-01_processed.mp4
├── kelas-02_processed.mp4
└── kelas-03_processed.mp4
```

### Exit code batch

- `0`: semua success/skip
- `1`: partial failure (ada video gagal)
- `2`: fatal startup/config/preflight
- `3`: tidak ada video input

Detail konfigurasi: lihat `scripts/batch_config.json` (termasuk `whisper_model_size`)  
Panduan lengkap: `docs/batch-processing.md`

Catatan: `cover_duration_sec` configurable per kebutuhan video.
- `0.0` = caption/watermark muncul normal dari awal (sesuai timestamp Whisper)
- `3.0` = 3 detik pertama tanpa caption/watermark (mis. video dengan cover opening)

## 📡 API Endpoints

### Videos
| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| POST | `/api/v1/videos/upload` | Upload video |
| GET | `/api/v1/videos/{video_id}` | Get metadata video |
| DELETE | `/api/v1/videos/{video_id}` | Hapus video |

### Captions
| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| POST | `/api/v1/videos/{video_id}/captions/generate` | Generate caption otomatis |
| GET | `/api/v1/videos/{video_id}/captions` | Get caption (SRT/VTT) |
| PUT | `/api/v1/videos/{video_id}/captions` | Update/edit caption |

### Watermarks
| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| POST | `/api/v1/watermarks/upload` | Upload watermark (PNG) |
| GET | `/api/v1/watermarks/{watermark_id}` | Get info watermark |
| DELETE | `/api/v1/watermarks/{watermark_id}` | Hapus watermark |

### Processing
| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| POST | `/api/v1/videos/{video_id}/process` | Process video (burn caption + watermark) |
| GET | `/api/v1/videos/{video_id}/output` | Download hasil |

### Jobs
| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| GET | `/api/v1/jobs/{job_id}` | Get status job |
| GET | `/api/v1/jobs` | List semua jobs |

## 🔄 Contoh Flow Lengkap

```bash
# 1. Upload video
curl -X POST "http://localhost:8000/api/v1/videos/upload" -F "file=@video.mp4"
# Response: {"video_id": "abc123", ...}

# 2. Generate caption
curl -X POST "http://localhost:8000/api/v1/videos/abc123/captions/generate" \
  -H "Content-Type: application/json" \
  -d '{"language": "id"}'
# Response: {"job_id": "job-xyz", "status": "pending"}

# 3. Cek status job
curl "http://localhost:8000/api/v1/jobs/job-xyz"
# Tunggu sampai status: "completed"

# 4. Upload watermark
curl -X POST "http://localhost:8000/api/v1/watermarks/upload" -F "file=@logo.png"
# Response: {"watermark_id": "wm-456", ...}

# 5. Process video
curl -X POST "http://localhost:8000/api/v1/videos/abc123/process" \
  -H "Content-Type: application/json" \
  -d '{"burn_captions": true, "watermark_id": "wm-456"}'

# 6. Download hasil
curl "http://localhost:8000/api/v1/videos/abc123/output" -o output.mp4
```

## ⚙️ Konfigurasi

Konfigurasi via environment variables. Lihat `.env.example`:

| Variable | Default | Deskripsi |
|----------|---------|-----------|
| `REDIS_HOST` | localhost | Redis host |
| `REDIS_PORT` | 6379 | Redis port |
| `STORAGE_BASE_PATH` | ./storage | Path penyimpanan file |
| `WHISPER_MODEL_SIZE` | base | Model whisper (tiny/base/small/medium/large) |
| `DEFAULT_CAPTION_LANGUAGE` | id | Bahasa default caption |
| `MAX_UPLOAD_SIZE_MB` | 500 | Max ukuran upload |

## 📁 Struktur Project

```
.
├── app/
│   ├── api/           # API endpoints
│   ├── models/        # Pydantic schemas
│   ├── services/      # Business logic
│   ├── tasks/         # Celery tasks
│   ├── storage/       # File storage layer
│   ├── config.py      # Configuration
│   └── main.py        # FastAPI app
├── tests/             # Test suite
├── storage/           # File storage (runtime)
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## 🧪 Testing

```bash
# Run semua tests
pytest

# Dengan coverage
pytest --cov=app

# Test spesifik
pytest tests/test_videos_api.py -v
```

## 🐳 Docker Services

| Service | Port | Deskripsi |
|---------|------|-----------|
| api | 8000 | FastAPI server |
| celery_worker | - | Background worker |
| redis | 6379 | Message broker |

## 📝 Watermark Options

| Parameter | Values | Default |
|-----------|--------|---------|
| position | top-left, top-right, bottom-left, bottom-right, center | bottom-right |
| opacity | 0.0 - 1.0 | 0.5 |

## 🤝 Contributing

Contributions welcome! Silakan buat Pull Request.

## 📄 License

MIT License - lihat [LICENSE](LICENSE) untuk detail.
