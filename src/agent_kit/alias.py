from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

MANAGED_ALIAS_MARKER = "# agent-kit managed alias: ak"
ALIAS_NAME = "ak"


@dataclass(slots=True, frozen=True)
class AliasStatus:
    alias_name: str
    path: Path
    bin_dir: Path
    state: str
    path_in_path: bool


@dataclass(slots=True, frozen=True)
class AliasMutationResult:
    alias_name: str
    path: Path
    changed: bool


def enable_alias(path: Path) -> AliasMutationResult:
    if _path_exists(path):
        if not is_managed_alias(path):
            raise ValueError(f"alias path is not managed by agent-kit: {path}")
        return AliasMutationResult(alias_name=ALIAS_NAME, path=path, changed=False)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_alias_wrapper(), encoding="utf-8")
    current_mode = stat.S_IMODE(path.stat().st_mode)
    path.chmod(current_mode | 0o755)
    return AliasMutationResult(alias_name=ALIAS_NAME, path=path, changed=True)


def disable_alias(path: Path) -> AliasMutationResult:
    if not _path_exists(path):
        return AliasMutationResult(alias_name=ALIAS_NAME, path=path, changed=False)
    if not is_managed_alias(path):
        raise ValueError(f"alias path is not managed by agent-kit: {path}")
    path.unlink()
    return AliasMutationResult(alias_name=ALIAS_NAME, path=path, changed=True)


def get_alias_status(path: Path) -> AliasStatus:
    if _path_exists(path):
        state = "enabled" if is_managed_alias(path) else "conflict"
    else:
        state = "disabled"

    return AliasStatus(
        alias_name=ALIAS_NAME,
        path=path,
        bin_dir=path.parent,
        state=state,
        path_in_path=is_path_in_environment_path(path.parent),
    )


def is_managed_alias(path: Path) -> bool:
    if not _path_exists(path) or path.is_dir():
        return False
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return MANAGED_ALIAS_MARKER in content


def render_alias_wrapper() -> str:
    return "\n".join(
        [
            "#!/usr/bin/env sh",
            MANAGED_ALIAS_MARKER,
            'exec agent-kit "$@"',
            "",
        ]
    )


def is_path_in_environment_path(path: Path) -> bool:
    expected = str(path.expanduser())
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry:
            continue
        if str(Path(entry).expanduser()) == expected:
            return True
    return False


def _path_exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()
