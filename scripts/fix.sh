#!/usr/bin/env bash

set -e

export PATH=env/bin:${PATH}

black db-auto-backup.py
isort db-auto-backup.py
