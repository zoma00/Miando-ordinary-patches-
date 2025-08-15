#!/bin/bash
# Build and run indikator_bot_turbo_fixed.py in Docker
# Usage: bash run_indikator_bot_turbo_live.sh

set -e

IMAGE_NAME=indikator_bot_turbo_live
CONTAINER_NAME=indikator-bot-turbo-live
SCRIPT=indikator_bot_turbo_fixed.py

cd /home/hazem/Miando/indikator_bot

echo "Building Docker image..."
docker build -t $IMAGE_NAME .

echo "Running container..."
docker run --rm -it \
  --name $CONTAINER_NAME \
  --network miando_default \
  -e DB_HOST=miando-db \
  -e DB_PORT=5432 \
  -e DB_NAME=miando \
  -e DB_USER=miando \
  -e DB_PASSWORD=changeme \
  -e SSL_CERT_PATH=/app/server.crt \
  -v $(pwd)/server.crt:/app/server.crt \
  $IMAGE_NAME \
  python3 $SCRIPT
