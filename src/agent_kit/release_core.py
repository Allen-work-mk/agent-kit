from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from packaging.version import Version


class ReleaseError(RuntimeError):
    pass


@dataclass(slots=True, frozen=True)
class ReleaseResult:
    version: str
    tag: str
    commit_message: str


class CoreReleaseTool:
    def __init__(
        self,
        *,
        repo_root: Path,
        git_runner=None,
        command_runner=None,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.git_runner = git_runner or self._run_git
        self.command_runner = command_runner or self._run_command

    def release(self, version_bump: str) -> ReleaseResult:
        self._ensure_clean_worktree()
        self._ensure_branch_available()

        pyproject_path = self.repo_root / "pyproject.toml"
        module_init_path = self.repo_root / "src" / "agent_kit" / "__init__.py"
        if not pyproject_path.exists():
            raise ReleaseError(f"缺少 core 版本文件: {pyproject_path.relative_to(self.repo_root)}")
        if not module_init_path.exists():
            raise ReleaseError(f"缺少 core 版本文件: {module_init_path.relative_to(self.repo_root)}")

        current_version = self._read_project_version(pyproject_path)
        new_version = self._bump_version(current_version, version_bump)
        tag_name = f"agent-kit-v{new_version}"
        commit_message = f"发布 agent-kit v{new_version}"

        self._ensure_tag_missing(tag_name)

        self._replace_pattern(
            pyproject_path,
            r'(?m)^version = "[^"]+"$',
            f'version = "{new_version}"',
            "core pyproject 版本号",
        )
        self._replace_pattern(
            module_init_path,
            r'(?m)^__version__ = "[^"]+"$',
            f'__version__ = "{new_version}"',
            "core __version__",
        )
        self._run_uv_lock()

        tracked_files = [pyproject_path, module_init_path]
        uv_lock_path = self.repo_root / "uv.lock"
        if uv_lock_path.exists():
            tracked_files.append(uv_lock_path)
        self._git(["git", "add", *[str(path.relative_to(self.repo_root)) for path in tracked_files]])
        self._git(["git", "commit", "-m", commit_message])
        self._git(["git", "tag", tag_name])
        return ReleaseResult(
            version=new_version,
            tag=tag_name,
            commit_message=commit_message,
        )

    def _ensure_clean_worktree(self) -> None:
        result = self._git(["git", "status", "--porcelain"])
        if result.stdout.strip():
            raise ReleaseError("工作区不干净，请先提交或清理变更")

    def _ensure_branch_available(self) -> None:
        result = self._git(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        if result.stdout.strip() == "HEAD":
            raise ReleaseError("当前处于 detached HEAD，不能创建发布提交")

    def _ensure_tag_missing(self, tag_name: str) -> None:
        result = self._git(["git", "tag", "--list", tag_name])
        if result.stdout.strip():
            raise ReleaseError(f"tag 已存在: {tag_name}")

    def _read_project_version(self, pyproject_path: Path) -> str:
        content = pyproject_path.read_text(encoding="utf-8")
        match = re.search(r'(?m)^version = "([^"]+)"$', content)
        if match is None:
            raise ReleaseError(f"无法解析版本号: {pyproject_path.relative_to(self.repo_root)}")
        return match.group(1)

    def _replace_pattern(
        self,
        path: Path,
        pattern: str,
        replacement: str,
        label: str,
    ) -> None:
        content = path.read_text(encoding="utf-8")
        updated, count = re.subn(pattern, replacement, content, count=1)
        if count != 1:
            raise ReleaseError(f"无法更新{label}: {path.relative_to(self.repo_root)}")
        path.write_text(updated, encoding="utf-8")

    def _bump_version(self, current_version: str, version_bump: str) -> str:
        if version_bump not in {"patch", "minor", "major"}:
            raise ReleaseError(f"不支持的版本升级类型: {version_bump}")
        parsed = Version(current_version)
        if parsed.pre or parsed.post or parsed.dev or len(parsed.release) != 3:
            raise ReleaseError(f"当前版本不支持自动升级: {current_version}")
        major, minor, patch = parsed.release
        if version_bump == "patch":
            return f"{major}.{minor}.{patch + 1}"
        if version_bump == "minor":
            return f"{major}.{minor + 1}.0"
        return f"{major + 1}.0.0"

    def _run_uv_lock(self) -> None:
        result = self.command_runner(
            ["uv", "lock"],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip() if getattr(result, "stderr", "") else "未知命令错误"
            raise ReleaseError(f"uv lock 执行失败: {stderr}")

    def _git(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        result = self.git_runner(args, capture_output=True, text=True)
        if result.returncode != 0:
            stderr = result.stderr.strip() if getattr(result, "stderr", "") else "未知 git 错误"
            raise ReleaseError(f"git 命令失败: {' '.join(args)}: {stderr}")
        return result

    def _run_git(self, args: list[str], *, capture_output: bool = True, text: bool = True):
        return subprocess.run(
            args,
            cwd=self.repo_root,
            capture_output=capture_output,
            text=text,
            check=False,
        )

    def _run_command(
        self,
        args: list[str],
        *,
        cwd: Path,
        capture_output: bool = True,
        text: bool = True,
    ):
        return subprocess.run(
            args,
            cwd=cwd,
            capture_output=capture_output,
            text=text,
            check=False,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="发布 core 并同步版本文件。")
    parser.add_argument("version_bump", choices=["patch", "minor", "major"])
    return parser


def main(argv: list[str] | None = None, *, repo_root: Path | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    tool = CoreReleaseTool(repo_root=(repo_root or Path.cwd()))
    result = tool.release(args.version_bump)
    print(f"已发布 agent-kit {result.version}，tag: {result.tag}")
    return 0
