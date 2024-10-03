#!/usr/bin/env bash

echo "*** Database only mode! ***"
docker compose -f docker-compose.database-only.yaml up -d && \
    docker ps -a
