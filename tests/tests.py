from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
from typing import Any, Callable

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
    exit_code, _ = run_backup({})
    assert exit_code == 0
    assert BACKUP_DIR.is_dir()
    assert sorted(normalize_container_name(f.name) for f in BACKUP_DIR.glob("*")) == [
        "docker-db-auto-backup-mariadb-1.sql",
        "docker-db-auto-backup-mysql-1.sql",
        "docker-db-auto-backup-psql-1.sql",
        "docker-db-auto-backup-redis-1.rdb",
    ]
    for backup_file in BACKUP_DIR.glob("*"):
        assert backup_file.stat().st_size > 0


@pytest.mark.parametrize(
    "algorithm,extension",
    [("gzip", ".gz"), ("lzma", ".xz"), ("xz", ".xz"), ("bz2", ".bz2"), ("plain", "")],
)
def test_compressed_file_extension(algorithm: str, extension: str) -> None:
    assert db_auto_backup.get_compressed_file_extension(algorithm) == extension
