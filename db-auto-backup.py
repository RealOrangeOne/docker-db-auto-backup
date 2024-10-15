#!/usr/bin/env python3
import bz2
import fnmatch
import gzip
import lzma
import os
import secrets
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import IO, Callable, Dict, Iterable, NamedTuple, Optional

import docker
import pycron
import requests
from docker.models.containers import Container
from dotenv import dotenv_values
from tqdm.auto import tqdm


class BackupProvider(NamedTuple):
    patterns: list[str]
    backup_method: Callable[[Container], str]
    file_extension: str


def get_container_env(container: Container) -> Dict[str, Optional[str]]:
    """
    Get all environment variables from a container.

    Variables at runtime, rather than those defined in the container.
    """
    _, (env_output, _) = container.exec_run("env", demux=True)
    return dict(dotenv_values(stream=StringIO(env_output.decode())))


def binary_exists_in_container(container: Container, binary_name: str) -> bool:
    """
    Get all environment variables from a container.

    Variables at runtime, rather than those defined in the container.
    """
    exit_code, _ = container.exec_run(["which", binary_name])
    return exit_code == 0


def temp_backup_file_name() -> str:
    """
    Create a temporary file to save backups to,
    then atomically replace backup file
    """
    return ".auto-backup-" + secrets.token_hex(4)


def open_file_compressed(file_path: Path, algorithm: str) -> IO[bytes]:
    file_path.touch(mode=0o600)

    if algorithm == "gzip":
        return gzip.open(file_path, mode="wb")  # type:ignore
    elif algorithm in ["lzma", "xz"]:
        return lzma.open(file_path, mode="wb")
    elif algorithm == "bz2":
        return bz2.open(file_path, mode="wb")
    elif algorithm == "plain":
        return file_path.open(mode="wb")
    raise ValueError(f"Unknown compression method {algorithm}")


def get_compressed_file_extension(algorithm: str) -> str:
    if algorithm == "gzip":
        return ".gz"
    elif algorithm in ["lzma", "xz"]:
        return ".xz"
    elif algorithm == "bz2":
        return ".bz2"
    elif algorithm == "plain":
        return ""
    raise ValueError(f"Unknown compression method {algorithm}")


def get_success_hook_url() -> Optional[str]:
    if success_hook_url := os.environ.get("SUCCESS_HOOK_URL"):
        return success_hook_url

    if healthchecks_id := os.environ.get("HEALTHCHECKS_ID"):
        healthchecks_host = os.environ.get("HEALTHCHECKS_HOST", "hc-ping.com")
        return f"https://{healthchecks_host}/{healthchecks_id}"

    if uptime_kuma_url := os.environ.get("UPTIME_KUMA_URL"):
        return uptime_kuma_url

    return None


def backup_psql(container: Container) -> str:
    env = get_container_env(container)
    user = env.get("POSTGRES_USER", "postgres")
    return f"pg_dumpall -U {user}"


def backup_mysql(container: Container) -> str:
    env = get_container_env(container)

    # The mariadb container supports both
    if "MARIADB_ROOT_PASSWORD" in env:
        auth = "-p$MARIADB_ROOT_PASSWORD"
    elif "MYSQL_ROOT_PASSWORD" in env:
        auth = "-p$MYSQL_ROOT_PASSWORD"
    else:
        raise ValueError(f"Unable to find MySQL root password for {container.name}")

    if binary_exists_in_container(container, "mariadb-dump"):
        backup_binary = "mariadb-dump"
    else:
        backup_binary = "mysqldump"

    return f"bash -c '{backup_binary} {auth} --all-databases'"


def backup_redis(container: Container) -> str:
    """
    Note: `SAVE` command locks the database, which isn't ideal.
    Hopefully the commit is fast enough!
    """
    return "sh -c 'redis-cli SAVE > /dev/null && cat /data/dump.rdb'"


BACKUP_PROVIDERS: list[BackupProvider] = [
    BackupProvider(
        patterns=["postgres", "tensorchord/pgvecto-rs", "nextcloud/aio-postgresql"],
        backup_method=backup_psql,
        file_extension="sql",
    ),
    BackupProvider(
        patterns=["mysql", "mariadb", "*/linuxserver/mariadb"],
        backup_method=backup_mysql,
        file_extension="sql",
    ),
    BackupProvider(
        patterns=["redis"], backup_method=backup_redis, file_extension="rdb"
    ),
]


BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", "/var/backups"))
SCHEDULE = os.environ.get("SCHEDULE", "0 0 * * *")
SHOW_PROGRESS = sys.stdout.isatty()
COMPRESSION = os.environ.get("COMPRESSION", "plain")
INCLUDE_LOGS = bool(os.environ.get("INCLUDE_LOGS"))


def get_backup_provider(container_names: Iterable[str]) -> Optional[BackupProvider]:
    for name in container_names:
        for provider in BACKUP_PROVIDERS:
            if any(fnmatch.fnmatch(name, pattern) for pattern in provider.patterns):
                return provider

    return None


def get_container_names(container: Container) -> Iterable[str]:
    """
    Extract names for a container from image tags or fallback to container name.
    """
    names = set()

    if container.image.tags:
        for tag in container.image.tags:
            image_name = tag.split(":")[0].split("@")[0]
            image_name = image_name.split("/")[-1]
            names.add(image_name)

    if not names and container.attrs.get("Config", {}).get("Image"):
        image_name = container.attrs["Config"]["Image"].split(":")[0].split("@")[0]
        image_name = image_name.split("/")[-1]
        names.add(image_name)

    if not names and container.name:
        names.add(container.name)

    return names

def is_swarm_mode() -> bool:
    docker_client = docker.from_env()
    info = docker_client.info()
    return info.get("Swarm", {}).get("LocalNodeState") == "active"


def get_local_node_id() -> str:
    docker_client = docker.from_env()
    info = docker_client.info()
    return info["Swarm"]["NodeID"]


def get_local_node_tasks() -> list:
    docker_client = docker.from_env()
    local_node_id = get_local_node_id()
    services = docker_client.services.list()

    local_tasks = []
    for service in services:
        tasks = service.tasks()
        for task in tasks:
            if task["NodeID"] == local_node_id and task["Status"]["State"] == "running":
                local_tasks.append(task)

    return local_tasks


def create_backup_file_name(container: Container, backup_provider: BackupProvider) -> Path:
    """
    Create a backup file name with a timestamp prefix and the container name.
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    container_name = container.name
    return BACKUP_DIR / f"{timestamp}_{container_name}.{backup_provider.file_extension}{get_compressed_file_extension(COMPRESSION)}"


@pycron.cron(SCHEDULE)
def backup(now: datetime) -> None:
    print("Starting backup...")

    docker_client = docker.from_env()

    if is_swarm_mode():
        print("Running in Swarm mode, adjusting container lookup...")
        tasks = get_local_node_tasks()
        backed_up_services = []

        for task in tasks:
            task_container_id = task['Status']['ContainerStatus']['ContainerID']
            try:
                container = docker_client.containers.get(task_container_id)
            except docker.errors.NotFound:
                continue

            container_names = get_container_names(container)
            backup_provider = get_backup_provider(container_names)
            
            if backup_provider is None:
                continue

            backup_file = create_backup_file_name(container, backup_provider)
            backup_temp_file_path = BACKUP_DIR / temp_backup_file_name()

            backup_command = backup_provider.backup_method(container)
            _, output = container.exec_run(backup_command, stream=True, demux=True)

            with open_file_compressed(
                backup_temp_file_path, COMPRESSION
            ) as backup_temp_file:
                with tqdm.wrapattr(
                    backup_temp_file,
                    method="write",
                    desc=task["ServiceID"],
                    disable=not SHOW_PROGRESS,
                ) as f:
                    for stdout, _ in output:
                        if stdout is None:
                            continue
                        f.write(stdout)

            os.replace(backup_temp_file_path, backup_file)
            backed_up_services.append(container.name)

        duration = (datetime.now() - now).total_seconds()
        print(f"Backup of {len(backed_up_services)} services complete in {duration:.2f} seconds.")
    else:
        containers = docker_client.containers.list()
        backed_up_containers = []

        for container in containers:
            container_names = get_container_names(container)
            backup_provider = get_backup_provider(container_names)

            if backup_provider is None:
                continue

            backup_file = create_backup_file_name(container, backup_provider)
            backup_temp_file_path = BACKUP_DIR / temp_backup_file_name()

            backup_command = backup_provider.backup_method(container)
            _, output = container.exec_run(backup_command, stream=True, demux=True)

            with open_file_compressed(
                backup_temp_file_path, COMPRESSION
            ) as backup_temp_file:
                with tqdm.wrapattr(
                    backup_temp_file,
                    method="write",
                    desc=container.name,
                    disable=not SHOW_PROGRESS,
                ) as f:
                    for stdout, _ in output:
                        if stdout is None:
                            continue
                        f.write(stdout)

            os.replace(backup_temp_file_path, backup_file)
            backed_up_containers.append(container.name)
        duration = (datetime.now() - now).total_seconds()
        print(
            f"Backup of {len(backed_up_containers)} containers complete in {duration:.2f} seconds."
        )

    if success_hook_url := get_success_hook_url():
        if INCLUDE_LOGS:
            response = requests.post(
                success_hook_url, data="\n".join(backed_up_containers or backed_up_services)
            )
        else:
            response = requests.get(success_hook_url)

        response.raise_for_status()


if __name__ == "__main__":
    if os.environ.get("SCHEDULE"):
        print(f"Running backup with schedule '{SCHEDULE}'.")
        pycron.start()
    else:
        backup(datetime.now())
