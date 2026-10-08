@echo off
cd /d "%~dp0"
echo Association Lab - first-time setup
echo Keep this window open. Python dependencies need internet access.
python -m venv .venv
if errorlevel 1 goto :failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :failed
if exist "data\raw\Disease_symptom_and_patient_profile_dataset.csv" goto :data_ready
".venv\Scripts\python.exe" scripts/download_data.py
if errorlevel 1 goto :failed
:data_ready
if exist "results\analysis.json" if exist "reports\DMDW6_Report.pdf" goto :analysis_ready
".venv\Scripts\python.exe" scripts/run_pipeline.py
if errorlevel 1 goto :failed
:analysis_ready
if exist "frontend\dist\index.html" goto :ready
echo Building the website. This step requires Node.js 22.12 or newer.
cd frontend
call npm.cmd ci
if errorlevel 1 goto :failed
call npm.cmd run build
if errorlevel 1 goto :failed
cd ..
:ready
echo Setup completed. Double-click START_PROJECT.cmd.
pause
exit /b 0
:failed
echo Setup failed. Read the error above; no successful setup is claimed.
pause
exit /b 1
