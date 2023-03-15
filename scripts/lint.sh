#!/usr/bin/env bash

set -e

export PATH=env/bin:${PATH}

set -x

black db-auto-backup.py --check

ruff check db-auto-backup.py

mypy db-auto-backup.py
