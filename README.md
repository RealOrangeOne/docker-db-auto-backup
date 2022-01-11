# docker-db-auto-backup

![](https://github.com/RealOrangeOne/docker-db-auto-backup/workflows/CI/badge.svg)

A script to automatically back up all databases running under docker on a host

## Supported databases

- MariaDB
- MySQL
- PostgreSQL

## Installation

This container requires access to the docker socket. This can be done either by mounting `/var/lib/docker.sock`, or using a HTTP proxy to provide it through `$DOCKER_HOST`.

Mount your backup directory as `/var/backups`. Backups will be saved here based on the name of the container. Backups are not dated or compressed.

Backups run daily, using cron's daily timer.
