#!/usr/bin/env python3

import fnmatch
from io import StringIO
from pathlib import Path
from typing import Callable, Dict, Optional, Sequence

import docker
from docker.models.containers import Container
from dotenv import dotenv_values

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
    return "bash -c 'mysqldump -p$MYSQL_ROOT_PASSWORD --all-databases'"


BACKUP_MAPPING: Dict[str, BackupCandidate] = {
    "postgres": backup_psql,
    "mysql": backup_mysql,
    "mariadb": backup_mysql,  # Basically the same thing
}

BACKUP_DIR = Path("/var/backups")


def get_backup_method(container_names: Sequence[str]) -> Optional[BackupCandidate]:
    for name in container_names:
        for container_pattern, backup_candidate in BACKUP_MAPPING.items():
            if fnmatch.fnmatch(name, container_pattern):
                return backup_candidate

    return None


def main() -> None:
    docker_client = docker.from_env()

    for container in docker_client.containers.list():
        container_names = [tag.rsplit(":", 1)[0] for tag in container.image.tags]
        backup_method = get_backup_method(container_names)
        if backup_method is None:
            continue

        backup_command = backup_method(container)
        backup_file = BACKUP_DIR / f"{container.name}.sql"
        print("Backing up", container.name, backup_file)
        _, output = container.exec_run(backup_command, stream=True, demux=True)

        with backup_file.open(mode="w") as f:
            for stdout, _ in output:
                if stdout is None:
                    continue
                f.write(stdout.decode())


if __name__ == "__main__":
    main()
