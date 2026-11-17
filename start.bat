@echo off
REM ---------------------------------------------------------------
REM  ByteBodega — one-click launcher for Windows
REM  Creates the virtual environment on first run, installs
REM  dependencies, then starts the Flask development server.
REM ---------------------------------------------------------------
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo.
        echo Python was not found. Install Python 3.10+ from python.org
        echo and tick "Add python.exe to PATH", then run this file again.
        pause
        exit /b 1
    )
)

echo Installing dependencies...
".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt

echo.
echo Starting ByteBodega on http://127.0.0.1:5000
echo Press CTRL+C to stop.
echo.
".venv\Scripts\python.exe" run.py

pause
