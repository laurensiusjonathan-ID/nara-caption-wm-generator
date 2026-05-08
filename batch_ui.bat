@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Nara Batch UI Launcher

set "ROOT=%~dp0"
cd /d "%ROOT%"

echo ============================================================
echo   NARA CUSTOMTKINTER BATCH UI LAUNCHER
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

echo [2/3] Activating virtual environment...
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

echo [3/3] Starting UI...
python -m ui_batch_app.main
set "UI_EXIT=%ERRORLEVEL%"

echo.
echo ============================================================
echo UI exited with code: %UI_EXIT%
echo ============================================================
echo.
pause
exit /b %UI_EXIT%
