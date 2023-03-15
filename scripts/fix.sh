#!/usr/bin/env bash

set -e

export PATH=env/bin:${PATH}

black db-auto-backup.py
ruff --fix db-auto-backup.py
