#!/bin/bash

set -e

echo "Stopping compose stack..."

docker compose down

echo "Stopping Postgres..."

docker stop lad-db || true

OLLAMA_PID_FILE=".ollama.pid"

echo "Stopping Ollama..."

if [ -f "$OLLAMA_PID_FILE" ]; then
  kill "$(cat "$OLLAMA_PID_FILE")" 2>/dev/null || true
  rm -f "$OLLAMA_PID_FILE"
else
  echo "Ollama wasn't started by start.sh, leaving it running."
fi

echo ""
echo "Cleanup complete."