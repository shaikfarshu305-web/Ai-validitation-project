@echo off
echo ============================================================
echo   AI Response Validation System
echo   Starting Backend API Server...
echo ============================================================
echo.
cd /d "%~dp0"
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
