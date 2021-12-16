#!/usr/bin/env python3

import fnmatch
from pathlib import Path
from typing import Callable, Dict, Optional, Sequence

import docker
from docker.models.containers import Container

BackupCandidate = Callable[[Container], str]


def backup_psql(container: Container) -> str:
    return "bash -c 'PGPASSWORD=$POSTGRES_PASSWORD pg_dumpall -U postgres'"


def backup_mysql(container: Container) -> str:
    return "bash -c 'mysqldump -p$MYSQL_ROOT_PASSWORD --all-databases'"


def backup_mariadb(container: Container) -> str:
    return "bash -c 'mysqldump -p$MARIADB_ROOT_PASSWORD --all-databases'"


BACKUP_MAPPING: Dict[str, BackupCandidate] = {
    "postgres": backup_psql,
    "mysql": backup_mysql,
    "mariadb": backup_mariadb,
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
            print(
                "Unsure how to backup",
                ", ".join([tag.rsplit(":", 1)[0] for tag in container.image.tags]),
            )
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
