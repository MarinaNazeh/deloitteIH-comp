#!/bin/bash
# Fresh Flow Insights - Run API + UI
# From project root. Requires: pip install -r requirements.txt

cd "$(dirname "$0")"
export PYTHONPATH="$PWD"

echo "Starting API on http://127.0.0.1:5000 ..."
python -m src.main &
API_PID=$!
sleep 3

echo ""
echo "Starting Streamlit UI..."
echo "Open http://localhost:8501 in your browser."
echo ""
streamlit run src/app_streamlit.py

kill $API_PID 2>/dev/null
