# docker-db-auto-backup

![](https://github.com/RealOrangeOne/docker-db-auto-backup/workflows/CI/badge.svg)

A script to automatically back up all databases running under docker on a host, with optional compression support.

## Supported databases

- MariaDB
- MySQL
- PostgreSQL
- Redis

## Installation

This container requires access to the docker socket. This can be done either by mounting `/var/lib/docker.sock`, or using a HTTP proxy to provide it through `$DOCKER_HOST`.

Mount your backup directory as `/var/backups` (or override `$BACKUP_DIR`). Backups will be saved here based on the name of the container. Backups are not dated or compressed.

Backups run daily at midnight. To change this, add a cron-style schedule to `$SCHEDULE`. For more information on the format of the cron strings, please see the [croniter documentation on PyPI](https://pypi.org/project/croniter/).

### Success hooks

When backups are completed successfully, a request can be made to the URL defined in `$SUCCESS_HOOK_URL`. By default, a `GET` request is made. To include logs, also set `$INCLUDE_LOGS` to a non-empty value, which sends a `POST` request instead with helpful details in the body.

Note: Previous versions also supported `$HEALTHCHECKS_ID`, `$HEALTHCHECKS_HOST` and `$UPTIME_KUMA_URL`, or native support for [healthchecks.io](https://healthchecks.io) and [Uptime Kuma](https://github.com/louislam/uptime-kuma/) respectively. These are all still supported, however `$SUCCESS_HOOK_URL` is preferred.

### Compression

Files are backed up uncompressed by default, on the assumption a snapshotting or native compressed filesystem is being used (eg ZFS). To enable compression, set `$COMPRESSION` to one of the supported algorithms:

- `gzip`
- `lzma` / `xz`
- `bz2`
- `plain` (no compression - the default)

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
      - SUCCESS_HOOK_URL=https://hc-ping.com/1234
      - INCLUDE_LOGS=true
```

### Oneshot

You may want to use this container to run backups just once, rather than on a schedule. To achieve this, set `$SCHEDULE` to an empty string, and the backup will run just once. This may be useful in conjunction with an external scheduler.
