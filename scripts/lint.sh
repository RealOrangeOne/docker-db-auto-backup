#!/usr/bin/env bash

set -e

export PATH=env/bin:${PATH}

set -x

black db-auto-backup.py tests --check

ruff check db-auto-backup.py tests

mypy db-auto-backup.py tests
