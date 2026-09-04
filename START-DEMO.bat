@echo off
REM SynthProof demo launcher. Starts the API, which also serves the console.
REM No npm, no build step. Verified 2026-08-24.
cd /d "%~dp0"
echo.
echo   SynthProof demo
echo   ---------------
echo   Console will be at  http://127.0.0.1:8000
echo   Keep this window open. Use a SECOND terminal for the CLI demo steps.
echo   Runbook: DEMO.md
echo.
start "" http://127.0.0.1:8000
.venv311\Scripts\python.exe -m uvicorn synthproof.api.main:app --host 127.0.0.1 --port 8000
pause
