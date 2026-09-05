#!/bin/bash

set -e

NETWORK_NAME="lad_network"

DB_CONTAINER="local_lad_db"
DB_IMAGE="local_lad_db_image"

echo "Checking docker network..."

if ! docker network inspect $NETWORK_NAME >/dev/null 2>&1; then
  echo "Creating docker network..."
  docker network create $NETWORK_NAME
fi

echo "Checking Postgres container..."

if [ "$(docker ps -q -f name=$DB_CONTAINER)" ]; then
  echo "Postgres already running."
else
  if [ "$(docker ps -aq -f name=$DB_CONTAINER)" ]; then
    echo "Starting existing Postgres container..."
    docker start $DB_CONTAINER
  else
    if ! docker image inspect $DB_IMAGE >/dev/null 2>&1; then
      echo "DB image missing. Building..."
      docker build -f infra/Dockerfile.db -t $DB_IMAGE infra
    fi

    echo "Creating Postgres container..."
    docker run -d --name $DB_CONTAINER --env-file infra/.db_env --network $NETWORK_NAME -p 5432:5432 $DB_IMAGE
  fi
fi

OLLAMA_PID_FILE=".ollama.pid"
OLLAMA_MODEL="qwen3:8b"

echo "Checking Ollama..."

if curl -s -o /dev/null http://localhost:11434; then
  echo "Ollama already running."
else
  echo "Starting Ollama..."
  nohup ollama serve >/tmp/ollama.log 2>&1 &
  echo $! >"$OLLAMA_PID_FILE"

  for _ in $(seq 1 15); do
    if curl -s -o /dev/null http://localhost:11434; then
      break
    fi
    sleep 1
  done
fi

if ! ollama list | grep -q "$OLLAMA_MODEL"; then
  echo "Pulling $OLLAMA_MODEL..."
  ollama pull "$OLLAMA_MODEL"
fi

echo "Starting app stack..."

docker compose up --build -d

echo "Done."