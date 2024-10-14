#!/usr/bin/env bash

set -e

export PATH=env/bin:${PATH}

echo "> Start all containers..."
docker compose up -d

echo "> Await postgres..."
until docker compose exec -T psql pg_isready -U postgres
do
  sleep 1
done

echo "> Await mysql..."
until docker compose exec -T mysql bash -c 'mysqladmin ping --protocol tcp -p$MYSQL_ROOT_PASSWORD'
do
  sleep 3
done

pytest -v

echo "> Clean up..."
docker compose down -t 3
