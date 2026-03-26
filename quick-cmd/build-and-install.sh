#!/usr/bin/env zsh
set -euo pipefail

# 在仓库根目录运行（以包含 `pyproject.toml` 的目录为准）。
cd "$(dirname "$0")/.."

# 避免当 `dist` 目录为空时，zsh 报 "no matches found"。
setopt NULL_GLOB

if [[ -d dist ]]; then
  rm -rf dist/*
fi

uv build

# 某些沙箱/CI 环境下，写入 `~/.local/share` 可能会失败。
# 如果默认的 XDG 数据目录不可写，就把 `uv tool install` 的安装数据重定向到当前仓库的 `.tmp/` 目录。
default_xdg_data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
if [[ ! -d "$default_xdg_data_home" || ! -w "$default_xdg_data_home" ]]; then
  export XDG_DATA_HOME="$PWD/.tmp/xdg-data"
fi

# 尽力让工具的 `bin` 目录在当前 shell 会话中可用（减少安装后再手动配置 PATH 的需要）。
data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
export PATH="${data_home%/}/../bin:$PATH"

# 从本地 `dist/` 安装构建产物对应版本到 `uv tool` 环境。
# 这里固定安装为 `pyproject.toml` 中声明的版本，确保与本次构建产物一致。
TOOL_VERSION="$(python -c 'import tomllib;print(tomllib.load(open("pyproject.toml","rb"))["project"]["version"])')"
uv tool install "agent-kit==${TOOL_VERSION}" --find-links dist --upgrade --force

