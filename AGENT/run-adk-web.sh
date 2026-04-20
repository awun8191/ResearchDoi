#!/bin/bash
# Script to run the ADK Web UI for the ResearchDoi Agent

# Move to the AGENT directory
cd "$(dirname "$0")"

# Ensure the virtual environment is used
if [ -d ".venv" ]; then
    export PATH="$(pwd)/.venv/bin:$PATH"
fi

# Set PYTHONPATH to include the current directory so 'src' is found
export PYTHONPATH=$PYTHONPATH:$(pwd)

echo "Starting ADK Web UI on http://127.0.0.1:8000..."
echo "Press Ctrl+C to stop."

# Run the adk web command pointing to the src directory
adk web --port 8000 src
