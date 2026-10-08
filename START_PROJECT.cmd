@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run SETUP_PROJECT.cmd first.
  pause
  exit /b 1
)
if not exist "frontend\dist\index.html" (
  echo Dashboard build missing. Run SETUP_PROJECT.cmd first.
  pause
  exit /b 1
)
echo Starting Association Lab at http://127.0.0.1:8000
".venv\Scripts\python.exe" scripts/launch.py
pause
