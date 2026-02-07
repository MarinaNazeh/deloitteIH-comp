@echo off
REM Fresh Flow Insights - Run API + UI (uses cache/ from build_cache.py)
cd /d "%~dp0"
set PYTHONPATH=%CD%

if not exist "cache\demand_daily.csv" (
    echo Cache not found. Run once: python scripts/build_cache.py
    pause
    exit /b 1
)

echo Starting API on http://127.0.0.1:5000 ...
start "Fresh Flow API" cmd /c "cd /d %~dp0 && set PYTHONPATH=%~dp0 && python -m src.main"

timeout /t 3 /nobreak >nul
echo Starting Streamlit UI - open http://localhost:8501
python -m streamlit run src/app_streamlit.py
