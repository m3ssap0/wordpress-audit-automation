#!/usr/bin/env bash

export SEMGREP_CONFIG=
docker compose down && \
    docker image rm wordpress-audit-automation-audit wordpress-audit-automation-database && \
    docker volume rm wordpress-audit-automation_database
unset SEMGREP_CONFIG