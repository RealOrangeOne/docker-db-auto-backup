#!/usr/bin/env python3

import fnmatch
import os
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Callable, Dict, Optional, Sequence

import docker
import pycron
import requests
from docker.models.containers import Container
from dotenv import dotenv_values
from tqdm.auto import tqdm

BackupCandidate = Callable[[Container], str]


def get_container_env(container: Container) -> Dict[str, Optional[str]]:
    """
    Get all environment variables from a container.

    Variables at runtime, rather than those defined in the container.
    """
    _, (env_output, _) = container.exec_run("env", demux=True)
    return dict(dotenv_values(stream=StringIO(env_output.decode())))


def backup_psql(container: Container) -> str:
    env = get_container_env(container)
    user = env.get("POSTGRES_USER", "postgres")
    return f"pg_dumpall -U {user}"


def backup_mysql(container: Container) -> str:
    env = get_container_env(container)

    # The mariadb container supports both
    if "MARIADB_ROOT_PASSWORD" in env:
        auth = "-p$MARIADB_ROOT_PASSWORD"
    else:
        auth = "-p$MYSQL_ROOT_PASSWORD"

    return f"bash -c 'mysqldump {auth} --all-databases'"


BACKUP_MAPPING: Dict[str, BackupCandidate] = {
    "postgres": backup_psql,
    "mysql": backup_mysql,
    "mariadb": backup_mysql,  # Basically the same thing
}

BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", "/var/backups"))
SCHEDULE = os.environ.get("SCHEDULE", "@daily")


def get_backup_method(container_names: Sequence[str]) -> Optional[BackupCandidate]:
    for name in container_names:
        for container_pattern, backup_candidate in BACKUP_MAPPING.items():
            if fnmatch.fnmatch(name, container_pattern):
                return backup_candidate

    return None


@pycron.cron(SCHEDULE)
def backup(timestamp: datetime) -> None:
    docker_client = docker.from_env()

    backed_up_containers = []

    for container in docker_client.containers.list():
        container_names = [tag.rsplit(":", 1)[0] for tag in container.image.tags]
        backup_method = get_backup_method(container_names)
        if backup_method is None:
            continue

        backup_command = backup_method(container)
        backup_file = BACKUP_DIR / f"{container.name}.sql"
        _, output = container.exec_run(backup_command, stream=True, demux=True)

        with tqdm.wrapattr(
            backup_file.open(mode="wb"), method="write", desc=container.name
        ) as f:
            for stdout, _ in output:
                if stdout is None:
                    continue
                f.write(stdout)

        backed_up_containers.append(container.name)

    if healthchecks_id := os.environ.get("HEALTHCHECKS_ID"):
        healthchecks_host = os.environ.get("HEALTHCHECKS_HOST", "hc-ping.com")
        requests.post(
            f"https://{healthchecks_host}/{healthchecks_id}",
            data="\n".join(backed_up_containers),
        ).raise_for_status()


if __name__ == "__main__":
    if os.environ.get("SCHEDULE"):
        pycron.start()
    else:
        backup(datetime.now())
