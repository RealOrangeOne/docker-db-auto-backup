#!/usr/bin/env bash

set -e

export PATH=env/bin:${PATH}

set -x

black db-auto-backup.py --check

flake8 db-auto-backup.py

isort -c db-auto-backup.py

mypy db-auto-backup.py
