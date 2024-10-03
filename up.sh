#!/usr/bin/env bash

if [ -z "$1" ]; then
    echo "Default Semgrep configuration."
    docker compose up -d && \ 
        docker ps -a
else
    export SEMGREP_CONFIG=$1
    echo "Custom Semgrep configuration: '$1'."
    docker compose -f docker-compose.yaml -f docker-compose.custom-semgrep-rules.yaml up -d && \
        docker ps -a
    unset SEMGREP_CONFIG
fi