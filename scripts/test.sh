#!/usr/bin/env bash

set -e

echo "> Start all containers..."
docker-compose up -d

echo "> Stop backup container..."
docker-compose stop backup

echo "> Await databases..."
# Only check postgres, that should be fine
docker-compose exec -T psql pg_isready -U postgres

echo "> Run backups..."
docker-compose run backup db-auto-backup

echo "> Clean up..."
docker-compose down
