#!/usr/bin/env zsh
set -euo pipefail

# Run from repository root (where pyproject.toml is).
cd "$(dirname "$0")/.."

# Avoid zsh "no matches found" when dist is empty.
setopt NULL_GLOB

if [[ -d dist ]]; then
  rm -rf dist/*
fi

uv build

# In some sandbox/CI environments, writing to ~/.local/share is not allowed.
# When the default XDG data dir is not writable, redirect tool installation into ./.
default_xdg_data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
if [[ ! -d "$default_xdg_data_home" || ! -w "$default_xdg_data_home" ]]; then
  export XDG_DATA_HOME="$PWD/.tmp/xdg-data"
fi

# Best-effort: make the tool's bin directory available to this shell session.
data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
export PATH="${data_home%/}/../bin:$PATH"

# Install the freshly built version as a `uv tool` from the local `dist/`.
# We pin to the version from pyproject.toml so the installed tool matches this build.
TOOL_VERSION="$(python -c 'import tomllib;print(tomllib.load(open("pyproject.toml","rb"))["project"]["version"])')"
uv tool install "agent-kit==${TOOL_VERSION}" --find-links dist --upgrade --force

