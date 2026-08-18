from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_STATE_ROOT = REPOSITORY_ROOT / "examples" / "state"
LOCAL_CONFIG = REPOSITORY_ROOT / ".jobtracker.json"
STATE_ENVIRONMENT_VARIABLE = "JOBTRACKER_STATE_DIR"


@dataclass(frozen=True)
class StatePaths:
    root: Path

    @property
    def jobs(self) -> Path:
        return self.root / "data" / "jobs.json"

    @property
    def companies(self) -> Path:
        return self.root / "data" / "companies.json"

    @property
    def career(self) -> Path:
        return self.root / "profile" / "career.json"

    @property
    def requirements(self) -> Path:
        return self.root / "profile" / "requirements.json"

    @property
    def matching(self) -> Path:
        return self.root / "profile" / "matching.json"

    @property
    def resume(self) -> Path:
        return self.root / "resume" / "resume.md"

    def required_files(self) -> tuple[Path, ...]:
        return (
            self.jobs,
            self.companies,
            self.career,
            self.requirements,
            self.matching,
            self.resume,
        )


def _expanded_path(value: str | Path, base: Path | None = None) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute() and base is not None:
        path = base / path
    return path.resolve(strict=False)


def _configured_state_dir(config_path: Path) -> Path | None:
    if not config_path.is_file():
        return None
    try:
        value = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{config_path} is not valid JSON: {exc}") from exc
    state_dir = value.get("state_dir") if isinstance(value, dict) else None
    if not isinstance(state_dir, str) or not state_dir.strip():
        raise ValueError(f"{config_path} must contain a non-empty state_dir string")
    return _expanded_path(state_dir, config_path.parent)


def resolve_state_paths(
    explicit: str | Path | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    repository_root: Path = REPOSITORY_ROOT,
) -> StatePaths:
    environment = os.environ if environ is None else environ
    if explicit:
        root = _expanded_path(explicit, Path.cwd())
    elif environment.get(STATE_ENVIRONMENT_VARIABLE):
        root = _expanded_path(environment[STATE_ENVIRONMENT_VARIABLE], Path.cwd())
    else:
        configured = _configured_state_dir(repository_root / LOCAL_CONFIG.name)
        root = configured or (Path.home() / ".smart-job-tracker").resolve(strict=False)
    return StatePaths(root)


def ensure_external_state_dir(state_root: Path, repository_root: Path = REPOSITORY_ROOT) -> None:
    state = state_root.resolve(strict=False)
    repository = repository_root.resolve(strict=False)
    if state == repository or repository in state.parents:
        raise ValueError("state directory must be outside the public repository")


def initialize_state(
    paths: StatePaths,
    *,
    source_root: Path = EXAMPLE_STATE_ROOT,
    repository_root: Path = REPOSITORY_ROOT,
) -> None:
    ensure_external_state_dir(paths.root, repository_root)
    source = source_root.expanduser().resolve(strict=False)
    missing = [path for path in StatePaths(source).required_files() if not path.is_file()]
    if missing:
        joined = ", ".join(str(path) for path in missing)
        raise ValueError(f"initialization source is incomplete: {joined}")
    if paths.root.exists() and any(paths.root.iterdir()):
        raise ValueError(f"state directory is not empty: {paths.root}")

    paths.root.mkdir(parents=True, mode=0o700, exist_ok=True)
    try:
        paths.root.chmod(0o700)
    except OSError:
        pass
    for directory in ("data", "profile", "resume"):
        target_directory = paths.root / directory
        target_directory.mkdir(mode=0o700, exist_ok=True)
        for source_file in (source / directory).iterdir():
            if not source_file.is_file():
                continue
            target_file = target_directory / source_file.name
            shutil.copy2(source_file, target_file)
            try:
                target_file.chmod(0o600)
            except OSError:
                pass


def missing_state_files(paths: StatePaths) -> list[Path]:
    return [path for path in paths.required_files() if not path.is_file()]
