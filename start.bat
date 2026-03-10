@echo off
title AgentApply AI - Job Application System
color 0A
echo.
echo  ============================================
echo   AgentApply AI - Automated Job Applications
echo  ============================================
echo.
echo  Starting backend server on http://localhost:8000
echo  Dashboard: http://localhost:3000
echo  Netlify:   https://agentapply-ai.netlify.app
echo.
echo  Press Ctrl+C to stop the server.
echo  ============================================
echo.

cd /d "%~dp0"

:: Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

:: Install dependencies if needed
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
    playwright install chromium
)

:: Start the backend server
echo Starting FastAPI backend...
python dashboard\server.py
pause
