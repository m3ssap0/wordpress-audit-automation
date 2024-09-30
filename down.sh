#!/usr/bin/env bash

export SEMGREP_CONFIG=
docker compose down && docker image rm wordpress-audit-automation-audit wordpress-audit-automation-database
unset SEMGREP_CONFIG