# docker-db-auto-backup

![](https://github.com/RealOrangeOne/docker-db-auto-backup/workflows/CI/badge.svg)

A script to automatically back up all databases running under docker on a host

## Supported databases

- MariaDB
- MySQL
- PostgreSQL
- Redis

## Installation

This container requires access to the docker socket. This can be done either by mounting `/var/lib/docker.sock`, or using a HTTP proxy to provide it through `$DOCKER_HOST`.

Mount your backup directory as `/var/backups` (or override `$BACKUP_DIR`). Backups will be saved here based on the name of the container. Backups are not dated or compressed.

Backups run daily, usually at midnight. To change this, add a cron-style schedule to `$SCHEDULE`. For more information on the format of the cron strings, please see the [croniter documentation on PyPI](https://pypi.org/project/croniter/).

Additionally, there is support for [healthchecks.io](https://healthchecks.io). `$HEALTHCHECKS_ID` can be used to specify the id to ping. If you're using a self-hosted instance, set `$HEALTHCHECKS_HOST`.

### Example `docker-compose.yml`

```yml
version: "2.3"

services:
  backup:
    image: ghcr.io/realorangeone/db-auto-backup:latest
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./backups:/var/backups
    environment:
      - HEALTHCHECKS_ID=id
```

### Oneshot

You may want to use this container to run backups just once, rather than on a schedule. To achieve this, set `$SCHEDULE` to an empty string, and the backup will run just once. This may be useful in conjunction with an external scheduler.
