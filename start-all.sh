#!/bin/bash

# start-all.sh - Runs ResearchDoi API, UI, and Agent in parallel
# Run: ./start-all.sh
# Stop: pkill -f uvicorn; pkill -f vite; pkill -f agent.py

set -e
echo "Starting API (port 8080)..."
cd API
uv run uvicorn main:app --host 0.0.0.0 --port 8080 --reload > api.log 2>&1 &

echo "Starting UI (port 5173)..."
cd ../ResearchDoi
npm run dev > ui.log 2>&1 &

echo "Starting Agent..."
cd ../AGENT
export PYTHONPATH=$PYTHONPATH:.
uv run adk web --port 8000 src > agent.log 2>&1 &

echo "All services started! Logs: api.log, ui.log, agent.log"
echo "API: http://localhost:8080/health"
echo "UI: http://localhost:5173"
