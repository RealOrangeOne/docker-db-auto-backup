#!/usr/bin/env bash

set -e

echo "> Start all containers..."
docker-compose up -d

echo "> Stop backup container..."
docker-compose stop backup

echo "> Await postgres..."
until docker-compose exec -T psql pg_isready -U postgres
do
  sleep 1
done
echo "> Await mysql..."
until docker-compose exec -T mysql bash -c 'mysqladmin ping --protocol tcp -p$MYSQL_ROOT_PASSWORD'
do
  sleep 1
done

echo "> Run backups..."
# Unset `$SCHEDULE` to run just once
docker-compose run -e "SCHEDULE=" backup ./db-auto-backup.py

echo "> Clean up..."
docker-compose down
