@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
title Nara Batch Video Processor

set "ROOT=%~dp0"
cd /d "%ROOT%"

echo ============================================================
echo   NARA CAPTION ^& WATERMARK BATCH PROCESSOR (LOCAL SIMPLE)
echo ============================================================
echo.

echo [1/3] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.11+ and add to PATH.
    pause
    exit /b 2
)
echo [OK] Python detected

echo [2/3] Activating virtual environment if available...
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo [OK] Using .venv
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo [OK] Using venv
) else (
    echo [ERROR] Virtual environment not found.
    echo Create one first:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 2
)

echo [3/3] Running local batch processor (no API/Celery)...
python scripts\batch_processor.py
set "PROCESSOR_EXIT=%ERRORLEVEL%"

echo.
echo ============================================================
echo Batch processing finished with exit code: %PROCESSOR_EXIT%
echo ============================================================
echo.
pause
exit /b %PROCESSOR_EXIT%
