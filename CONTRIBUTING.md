# Contributing

Terima kasih sudah tertarik untuk berkontribusi! 🎉

## Cara Berkontribusi

### Reporting Bugs

1. Cek [Issues](../../issues) untuk memastikan bug belum dilaporkan
2. Buat issue baru dengan template bug report
3. Sertakan langkah reproduksi yang jelas

### Feature Requests

1. Cek [Issues](../../issues) untuk memastikan fitur belum diusulkan
2. Buat issue baru dengan template feature request
3. Jelaskan use case dan manfaatnya

### Pull Requests

1. Fork repository
2. Buat branch baru: `git checkout -b feature/nama-fitur`
3. Commit changes: `git commit -m "Add: deskripsi singkat"`
4. Push ke branch: `git push origin feature/nama-fitur`
5. Buat Pull Request

## Development Setup

```bash
# Clone fork kamu
git clone https://github.com/username/video-caption-watermark-api.git
cd video-caption-watermark-api

# Buat virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# atau
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install pytest pytest-cov black isort flake8

# Run tests
pytest
```

## Code Style

- Gunakan [Black](https://black.readthedocs.io/) untuk formatting
- Gunakan [isort](https://pycqa.github.io/isort/) untuk import sorting
- Follow PEP 8 guidelines

```bash
# Format code
black app/ tests/
isort app/ tests/

# Check linting
flake8 app/ tests/
```

## Commit Messages

Format: `<type>: <description>`

Types:
- `Add` - Fitur baru
- `Fix` - Bug fix
- `Update` - Update existing feature
- `Remove` - Hapus code/file
- `Refactor` - Refactoring
- `Docs` - Dokumentasi
- `Test` - Testing

Contoh:
```
Add: endpoint untuk batch video processing
Fix: error handling pada caption generation
Docs: update API documentation
```

## Testing

- Tulis test untuk setiap fitur baru
- Pastikan semua test pass sebelum submit PR
- Target coverage minimal 80%

```bash
# Run tests dengan coverage
pytest --cov=app --cov-report=html
```

## Questions?

Buat issue dengan label `question` atau hubungi maintainer.
