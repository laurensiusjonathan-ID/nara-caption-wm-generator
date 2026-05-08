# Panduan Menjalankan Video Caption Watermark API

## Prasyarat

- Docker & Docker Compose terinstall
- Sample video file (MP4/MOV/AVI)
- Sample watermark image (PNG dengan transparansi)

## Step 1: Start Services

```bash
# Copy environment file
cp .env.example .env

# Start semua services
docker-compose up -d

# Cek status
docker-compose ps

# Pastikan semua services running
docker-compose logs -f
```

Tunggu sampai muncul log: `Application startup complete`

## Step 2: Akses API

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health

## Step 3: Test Flow Lengkap

### 3.1 Upload Video

```bash
curl -X POST "http://localhost:8000/api/v1/videos/upload" \
  -F "file=@sample.mp4"
```

Response:
```json
{
  "video_id": "abc123",
  "filename": "sample.mp4",
  "duration": 120.5,
  "resolution": "1920x1080",
  "file_size": 15000000
}
```

Simpan `video_id` untuk langkah selanjutnya.

### 3.2 Generate Caption

```bash
curl -X POST "http://localhost:8000/api/v1/videos/{video_id}/captions/generate" \
  -H "Content-Type: application/json" \
  -d '{"language": "id", "format": "srt"}'
```

Response:
```json
{
  "job_id": "job-xyz789",
  "status": "pending"
}
```

### 3.3 Cek Status Job Caption

```bash
curl "http://localhost:8000/api/v1/jobs/{job_id}"
```

Tunggu sampai status `completed`.

### 3.4 Lihat Caption yang Dihasilkan

```bash
curl "http://localhost:8000/api/v1/videos/{video_id}/captions"
```

### 3.5 Upload Watermark

```bash
curl -X POST "http://localhost:8000/api/v1/watermarks/upload" \
  -F "file=@logo.png"
```

Response:
```json
{
  "watermark_id": "wm-456",
  "filename": "logo.png"
}
```

### 3.6 Process Video (Burn Caption + Watermark)

```bash
curl -X POST "http://localhost:8000/api/v1/videos/{video_id}/process" \
  -H "Content-Type: application/json" \
  -d '{
    "burn_captions": true,
    "watermark_id": "{watermark_id}",
    "watermark_position": "bottom-right",
    "watermark_opacity": 0.5
  }'
```

Response:
```json
{
  "job_id": "job-process-123",
  "status": "pending"
}
```

### 3.7 Monitor Progress

```bash
# Cek status processing
curl "http://localhost:8000/api/v1/jobs/{job_id}"
```

### 3.8 Download Hasil

Setelah status `completed`:

```bash
curl "http://localhost:8000/api/v1/videos/{video_id}/output" -o output.mp4
```

## Troubleshooting

### Cek Logs

```bash
# Semua logs
docker-compose logs -f

# API logs saja
docker-compose logs -f api

# Celery worker logs
docker-compose logs -f celery_worker
```

### Restart Services

```bash
docker-compose restart
```

### Stop & Clean

```bash
# Stop services
docker-compose down

# Stop dan hapus volumes
docker-compose down -v
```

## Tips

1. Gunakan Swagger UI (http://localhost:8000/docs) untuk testing interaktif
2. File yang di-upload tersimpan di folder `./storage/`
3. Untuk video besar, processing bisa memakan waktu - pantau via job status
4. Default bahasa caption adalah Indonesian (`id`)
