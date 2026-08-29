#!/bin/bash

set -e

echo "Stopping compose stack..."

docker compose down

echo "Stopping Postgres..."

docker stop local_lad_db || true

echo ""
echo "Cleanup complete."
