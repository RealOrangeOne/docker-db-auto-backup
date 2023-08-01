from pathlib import Path
from typing import Any, Callable

import docker
import pytest

BACKUP_DIR = Path.cwd() / "backups"


@pytest.fixture
def run_backup(request: Any) -> Callable:
    docker_client = docker.from_env()
    backup_container = docker_client.containers.get("docker-db-auto-backup-backup-1")

    def clean_backups() -> None:
        # HACK: Remove files from inside container to avoid permissions issue
        backup_container.exec_run(["rm", "-rf", "/var/backups"])

    def _run_backup(env: dict) -> Any:
        return backup_container.exec_run(
            [
                "./db-auto-backup.py",
            ],
            environment={**env, "SCHEDULE": ""},
        )

    request.addfinalizer(clean_backups)

    return _run_backup
