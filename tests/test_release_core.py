from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def require_module(name: str):
    try:
        return importlib.import_module(name)
    except Exception as exc:  # pragma: no cover - used for red phase
        pytest.fail(f"could not import {name}: {exc}")


def _build_repo(tmp_path: Path, *, version: str = "0.1.0", include_version: bool = True) -> Path:
    repo_root = tmp_path / "repo"
    package_root = repo_root / "src" / "agent_kit"
    package_root.mkdir(parents=True, exist_ok=True)

    pyproject_lines = ['[project]\n', 'name = "agent-kit"\n']
    if include_version:
        pyproject_lines.append(f'version = "{version}"\n')
    (repo_root / "pyproject.toml").write_text("".join(pyproject_lines), encoding="utf-8")

    package_root.joinpath("__init__.py").write_text(
        f'__version__ = "{version}"\n',
        encoding="utf-8",
    )
    repo_root.joinpath("uv.lock").write_text(
        f'[[package]]\nname = "agent-kit"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    return repo_root


def _git_runner(*, clean: bool = True, tag_exists: bool = False, detached_head: bool = False):
    commands: list[list[str]] = []

    def run(args: list[str], *, capture_output: bool = True, text: bool = True):
        commands.append(list(args))
        if args[:3] == ["git", "status", "--porcelain"]:
            stdout = "" if clean else " M pyproject.toml\n"
            return type("Result", (), {"returncode": 0, "stdout": stdout, "stderr": ""})()
        if args[:4] == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
            stdout = "HEAD\n" if detached_head else "feature/release\n"
            return type("Result", (), {"returncode": 0, "stdout": stdout, "stderr": ""})()
        if args[:3] == ["git", "tag", "--list"]:
            stdout = f"{args[3]}\n" if tag_exists else ""
            return type("Result", (), {"returncode": 0, "stdout": stdout, "stderr": ""})()
        if args[:2] == ["git", "add"]:
            return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        if args[:2] == ["git", "commit"]:
            version = args[-1].split(" v", 1)[1]
            return type("Result", (), {"returncode": 0, "stdout": f"[feature/release] 发布 agent-kit v{version}\n", "stderr": ""})()
        if args[:2] == ["git", "tag"]:
            return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        raise AssertionError(f"unexpected git command: {args}")

    return commands, run


def _command_runner(lock_content: str | None = None, *, fail: bool = False):
    commands: list[list[str]] = []

    def run(args: list[str], *, cwd: Path, capture_output: bool = True, text: bool = True):
        commands.append(list(args))
        if args == ["uv", "lock"]:
            if fail:
                return type("Result", (), {"returncode": 1, "stdout": "", "stderr": "lock failed"})()
            if lock_content is not None:
                cwd.joinpath("uv.lock").write_text(lock_content, encoding="utf-8")
            return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        raise AssertionError(f"unexpected command: {args}")

    return commands, run


def test_release_core_patch_updates_versions_and_git_tag(tmp_path: Path):
    release_module = require_module("agent_kit.release_core")
    repo_root = _build_repo(tmp_path)
    commands, git_runner = _git_runner()
    command_calls, command_runner = _command_runner(
        lock_content='[[package]]\nname = "agent-kit"\nversion = "0.1.1"\n'
    )
    releaser = release_module.CoreReleaseTool(
        repo_root=repo_root,
        git_runner=git_runner,
        command_runner=command_runner,
    )

    result = releaser.release("patch")

    assert result.version == "0.1.1"
    assert result.tag == "agent-kit-v0.1.1"
    assert result.commit_message == "发布 agent-kit v0.1.1"
    assert 'version = "0.1.1"' in (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    assert '__version__ = "0.1.1"' in (repo_root / "src" / "agent_kit" / "__init__.py").read_text(encoding="utf-8")
    assert ["git", "commit", "-m", "发布 agent-kit v0.1.1"] in commands
    assert ["git", "tag", "agent-kit-v0.1.1"] in commands
    assert ["git", "add", "pyproject.toml", "src/agent_kit/__init__.py", "uv.lock"] in commands
    assert command_calls == [["uv", "lock"]]


@pytest.mark.parametrize("bump, expected", [("minor", "0.2.0"), ("major", "1.0.0")])
def test_release_core_supports_minor_and_major_bumps(tmp_path: Path, bump: str, expected: str):
    release_module = require_module("agent_kit.release_core")
    repo_root = _build_repo(tmp_path)
    _, git_runner = _git_runner()
    _, command_runner = _command_runner()
    releaser = release_module.CoreReleaseTool(
        repo_root=repo_root,
        git_runner=git_runner,
        command_runner=command_runner,
    )

    result = releaser.release(bump)

    assert result.version == expected
    assert result.tag == f"agent-kit-v{expected}"


def test_release_core_rejects_dirty_worktree(tmp_path: Path):
    release_module = require_module("agent_kit.release_core")
    repo_root = _build_repo(tmp_path)
    _, git_runner = _git_runner(clean=False)
    releaser = release_module.CoreReleaseTool(repo_root=repo_root, git_runner=git_runner)

    with pytest.raises(release_module.ReleaseError, match="工作区不干净"):
        releaser.release("patch")


def test_release_core_rejects_detached_head(tmp_path: Path):
    release_module = require_module("agent_kit.release_core")
    repo_root = _build_repo(tmp_path)
    _, git_runner = _git_runner(detached_head=True)
    releaser = release_module.CoreReleaseTool(repo_root=repo_root, git_runner=git_runner)

    with pytest.raises(release_module.ReleaseError, match="detached HEAD"):
        releaser.release("patch")


def test_release_core_rejects_existing_tag(tmp_path: Path):
    release_module = require_module("agent_kit.release_core")
    repo_root = _build_repo(tmp_path)
    _, git_runner = _git_runner(tag_exists=True)
    releaser = release_module.CoreReleaseTool(repo_root=repo_root, git_runner=git_runner)

    with pytest.raises(release_module.ReleaseError, match="tag 已存在"):
        releaser.release("patch")


def test_release_core_rejects_invalid_current_version(tmp_path: Path):
    release_module = require_module("agent_kit.release_core")
    repo_root = _build_repo(tmp_path, version="0.1.0rc1")
    _, git_runner = _git_runner()
    releaser = release_module.CoreReleaseTool(repo_root=repo_root, git_runner=git_runner)

    with pytest.raises(release_module.ReleaseError, match="当前版本不支持自动升级"):
        releaser.release("patch")


def test_release_core_rejects_missing_pyproject_version(tmp_path: Path):
    release_module = require_module("agent_kit.release_core")
    repo_root = _build_repo(tmp_path, include_version=False)
    _, git_runner = _git_runner()
    releaser = release_module.CoreReleaseTool(repo_root=repo_root, git_runner=git_runner)

    with pytest.raises(release_module.ReleaseError, match="无法解析版本号"):
        releaser.release("patch")


def test_release_core_stops_when_uv_lock_fails(tmp_path: Path):
    release_module = require_module("agent_kit.release_core")
    repo_root = _build_repo(tmp_path)
    commands, git_runner = _git_runner()
    _, command_runner = _command_runner(fail=True)
    releaser = release_module.CoreReleaseTool(
        repo_root=repo_root,
        git_runner=git_runner,
        command_runner=command_runner,
    )

    with pytest.raises(release_module.ReleaseError, match="uv lock 执行失败"):
        releaser.release("patch")

    assert ["git", "commit", "-m", "发布 agent-kit v0.1.1"] not in commands
