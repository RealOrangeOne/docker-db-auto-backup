# docker-db-auto-backup

![](https://github.com/RealOrangeOne/docker-db-auto-backup/workflows/CI/badge.svg)

A script to automatically back up all databases running under docker on a host

## Supported databases

- MariaDB
- MySQL
- PostgreSQL
- Redis

## Installation

This container requires access to the docker socket. This should always be done, for security reasons, using a [HTTP proxy](https://github.com/Tecnativa/docker-socket-proxy) which this container can then access through the `DOCKER_HOST` environment variable. 

You can use this container by directly mounting `/var/lib/docker.sock` but this is not recommended.

Mount your backup directory as `/var/backups` (or override `BACKUP_DIR`). Backups will be saved here based on the name of the container. Backups are not dated or compressed.

Backups run daily at midnight. To change this, add a cron-style schedule to `SCHEDULE`. For more information on the format of the cron strings, please see the [croniter documentation on PyPI](https://pypi.org/project/croniter/).

Additionally, there is support for [healthchecks.io](https://healthchecks.io). `HEALTHCHECKS_ID` can be used to specify the id to ping. If you're using a self-hosted instance, set `HEALTHCHECKS_HOST`.

### Example `docker-compose.yml` 

```yml
---
version: "3.8"
   
services:
  
  db-auto-backup:
    image: ghcr.io/realorangeone/db-auto-backup:latest
    container_name: db-auto-backup
    volumes:
      - /mnt/db-backups:/var/backups:rw
    environment: 
      - DOCKER_HOST=tcp://docker-socket-proxy:2375
    depends_on:
      - docker-socket-proxy
    networks:
      - docker-socket-proxy-net      
    restart: unless-stopped      

  docker-socket-proxy:
    image: tecnativa/docker-socket-proxy:latest
    container_name: docker-socket-proxy
    environment:
      - POST=1
      - CONTAINERS=1
      - IMAGES=1
      - EXEC=1
    networks:
      - docker-socket-proxy-net
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    restart: unless-stopped
    
networks:
  docker-socket-proxy-net:
    internal: true
```

### Oneshot

You may want to use this container to run backups just once, rather than on a schedule (or perhaps with an external scheduler). To achieve this, run these commands on the host running docker:

`docker exec db-auto-backup SCHEDULE=`

`docker exec ./db-auto-backup.py`
