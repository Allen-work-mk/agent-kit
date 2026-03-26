from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _build_repo(tmp_path: Path) -> Path:
    source_script = REPO_ROOT / "scripts" / "release" / "ak-core-release.sh"
    if not source_script.exists():  # pragma: no cover - red phase
        pytest.fail(f"missing script under test: {source_script}")

    repo_root = tmp_path / "repo"
    (repo_root / "scripts" / "release").mkdir(parents=True, exist_ok=True)

    shutil.copy2(source_script, repo_root / "scripts" / "release" / "ak-core-release.sh")
    (repo_root / "scripts" / "release" / "release_core.py").write_text(
        "import sys\nprint('release:' + ' '.join(sys.argv[1:]))\n",
        encoding="utf-8",
    )
    return repo_root


def _run(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "scripts/release/ak-core-release.sh", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )


def test_core_release_shortcut_passes_through_to_release_script(tmp_path: Path) -> None:
    repo_root = _build_repo(tmp_path)

    result = _run(repo_root, "patch")

    assert result.returncode == 0, result.stderr or result.stdout
    assert result.stdout.strip() == "release:patch"


def test_core_release_shortcut_without_args_shows_usage(tmp_path: Path) -> None:
    repo_root = _build_repo(tmp_path)

    result = _run(repo_root)

    assert result.returncode == 1
    assert "用法" in result.stderr
    assert "patch" in result.stderr
    assert "minor" in result.stderr
    assert "major" in result.stderr


def test_core_release_shortcut_rejects_unknown_bump_type(tmp_path: Path) -> None:
    repo_root = _build_repo(tmp_path)

    result = _run(repo_root, "foo")

    assert result.returncode == 1
    assert "版本类型无效" in result.stderr
    assert "patch" in result.stderr
    assert "minor" in result.stderr
    assert "major" in result.stderr


def test_core_release_shortcut_rejects_extra_args(tmp_path: Path) -> None:
    repo_root = _build_repo(tmp_path)

    result = _run(repo_root, "patch", "extra")

    assert result.returncode == 1
    assert "参数数量不正确" in result.stderr
    assert "patch" in result.stderr


def test_core_release_shortcut_help_uses_usage_output(tmp_path: Path) -> None:
    repo_root = _build_repo(tmp_path)

    result = _run(repo_root, "--help")

    assert result.returncode == 0
    assert "用法" in result.stdout
    assert "patch" in result.stdout
