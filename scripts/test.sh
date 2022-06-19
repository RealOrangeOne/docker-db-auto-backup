#!/usr/bin/env bash

set -e

echo "> Start all containers..."
docker-compose up -d

echo "> Stop backup container..."
docker-compose stop backup

echo "> Await databases..."
# Only check postgres, that should be fine
until docker-compose exec -T psql pg_isready -U postgres
do
  sleep 1
done

echo "> Run backups..."
docker-compose run backup ./db-auto-backup.py

echo "> Clean up..."
docker-compose down
