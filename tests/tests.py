from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
from typing import Any, Callable
from unittest.mock import MagicMock

import docker
import pytest

BACKUP_DIR = Path.cwd() / "backups"


def import_file(path: Path) -> Any:
    """
    Import a module from a file path, returning its contents.
    """
    loader = SourceFileLoader(path.name, str(path))
    spec = spec_from_loader(path.name, loader)
    assert spec is not None
    mod = module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def normalize_container_name(container_name: str) -> str:
    return container_name.replace("_", "-")


# HACK: The filename isn't compatible with `import foo` syntax
db_auto_backup = import_file(Path.cwd() / "db-auto-backup.py")


def test_backup_runs(run_backup: Callable) -> None:
    exit_code, out = run_backup({})
    assert exit_code == 0, out
    assert BACKUP_DIR.is_dir()
    assert sorted(normalize_container_name(f.name) for f in BACKUP_DIR.iterdir()) == [
        "docker-db-auto-backup-mariadb-1.sql",
        "docker-db-auto-backup-mysql-1.sql",
        "docker-db-auto-backup-psql-1.sql",
        "docker-db-auto-backup-redis-1.rdb",
    ]
    for backup_file in BACKUP_DIR.iterdir():
        assert backup_file.stat().st_size > 50
        assert (backup_file.stat().st_mode & 0o777) == 0o600


@pytest.mark.parametrize(
    "algorithm,extension",
    [("gzip", ".gz"), ("lzma", ".xz"), ("xz", ".xz"), ("bz2", ".bz2"), ("plain", "")],
)
def test_backup_runs_compressed(
    run_backup: Callable, algorithm: str, extension: str
) -> None:
    exit_code, out = run_backup({"COMPRESSION": algorithm})
    assert exit_code == 0, out
    assert BACKUP_DIR.is_dir()
    assert sorted(normalize_container_name(f.name) for f in BACKUP_DIR.iterdir()) == [
        f"docker-db-auto-backup-mariadb-1.sql{extension}",
        f"docker-db-auto-backup-mysql-1.sql{extension}",
        f"docker-db-auto-backup-psql-1.sql{extension}",
        f"docker-db-auto-backup-redis-1.rdb{extension}",
    ]
    for backup_file in BACKUP_DIR.iterdir():
        assert (backup_file.stat().st_mode & 0o777) == 0o600


@pytest.mark.parametrize(
    "algorithm,extension",
    [("gzip", ".gz"), ("lzma", ".xz"), ("xz", ".xz"), ("bz2", ".bz2"), ("plain", "")],
)
def test_compressed_file_extension(algorithm: str, extension: str) -> None:
    assert db_auto_backup.get_compressed_file_extension(algorithm) == extension


def test_success_hook_url(monkeypatch: Any) -> None:
    monkeypatch.setenv("SUCCESS_HOOK_URL", "https://example.com")
    assert db_auto_backup.get_success_hook_url() == "https://example.com"


def test_healthchecks_success_hook_url(monkeypatch: Any) -> None:
    monkeypatch.setenv("HEALTHCHECKS_ID", "1234")
    assert db_auto_backup.get_success_hook_url() == "https://hc-ping.com/1234"


def test_healthchecks_success_hook_url_custom_host(monkeypatch: Any) -> None:
    monkeypatch.setenv("HEALTHCHECKS_ID", "1234")
    monkeypatch.setenv("HEALTHCHECKS_HOST", "my-healthchecks.com")
    assert db_auto_backup.get_success_hook_url() == "https://my-healthchecks.com/1234"


def test_uptime_kuma_success_hook_url(monkeypatch: Any) -> None:
    monkeypatch.setenv("UPTIME_KUMA_URL", "https://uptime-kuma.com")
    assert db_auto_backup.get_success_hook_url() == "https://uptime-kuma.com"


@pytest.mark.parametrize(
    "tag,name",
    [
        ("postgres:14-alpine", "postgres"),
        ("docker.io/postgres:14-alpine", "postgres"),
        ("ghcr.io/realorangeone/db-auto-backup:latest", "realorangeone/db-auto-backup"),
        ("theorangeone/db-auto-backup:latest:latest", "theorangeone/db-auto-backup"),
        ("lscr.io/linuxserver/mariadb:latest", "linuxserver/mariadb"),
        ("docker.io/library/postgres:14-alpine", "postgres"),
        ("library/postgres:14-alpine", "postgres"),
    ],
)
def test_get_container_names(tag: str, name: str) -> None:
    container = MagicMock()
    container.image.tags = [tag]
    assert db_auto_backup.get_container_names(container) == {name}


@pytest.mark.parametrize(
    "container_name,name",
    [
        ("postgres", "postgres"),
        ("mysql", "mysql"),
        ("mariadb", "mysql"),
        ("linuxserver/mariadb", "mysql"),
        ("tensorchord/pgvecto-rs", "postgres"),
        ("nextcloud/aio-postgresql", "postgres"),
        ("redis", "redis"),
    ],
)
def test_get_backup_provider(container_name: str, name: str) -> None:
    provider = db_auto_backup.get_backup_provider([container_name])

    assert provider is not None
    assert provider.name == name


# Have to be run with root privileges to avoid permission issues
def test_backup_runs_clean(run_backup: Callable) -> None:
    exit_code, out = run_backup({"CLEAN": "true"})
    assert exit_code == 0, out
    assert BACKUP_DIR.is_dir()
    assert sorted(normalize_container_name(f.name) for f in BACKUP_DIR.iterdir()) == [
        "docker-db-auto-backup-mariadb-1.sql",
        "docker-db-auto-backup-mysql-1.sql",
        "docker-db-auto-backup-psql-1.sql",
        "docker-db-auto-backup-redis-1.rdb",
    ]
    # Hack for having right on files
    docker_client = docker.from_env()
    backup_container = docker_client.containers.get("docker-db-auto-backup")

    for backup_file in BACKUP_DIR.iterdir():
        backup_container.exec_run(["chmod", "o+r", f"/var/backups/{backup_file.name}"])
        if "sql" in backup_file.name:
            with open(backup_file, "r") as f:
                content = f.read()
                if "psql" in backup_file.name:
                    assert content.find("\nDROP DATABASE") > 0
                    assert content.find("\nCREATE DATABASE") > 0
                if "mysql" in backup_file.name or "mariadb" in backup_file.name:
                    assert content.find("/*!40000 DROP DATABASE IF EXISTS") > 0
                    assert content.find("CREATE DATABASE /*!32312 IF NOT EXISTS*/ ") > 0
                    assert content.find("CREATE TABLE IF NOT EXISTS ") > 0
