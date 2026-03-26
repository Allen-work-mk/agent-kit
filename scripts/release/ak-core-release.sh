#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
readonly BUMP_TYPES=("patch" "minor" "major")


print_usage() {
  local output="${1:-stderr}"
  local fd=2
  if [[ "$output" == "stdout" ]]; then
    fd=1
  fi

  {
    echo "用法: ./scripts/release/ak-core-release.sh <patch|minor|major>"
    echo "可用版本类型: ${BUMP_TYPES[*]}"
  } >&"$fd"
}


bump_is_valid() {
  local target="$1"
  local bump
  for bump in "${BUMP_TYPES[@]}"; do
    if [[ "$bump" == "$target" ]]; then
      return 0
    fi
  done
  return 1
}


if [[ $# -eq 1 ]] && [[ "$1" == "--help" || "$1" == "-h" ]]; then
  print_usage stdout
  exit 0
fi

if [[ $# -eq 0 ]]; then
  echo "缺少参数。" >&2
  print_usage stderr
  exit 1
fi

version_bump="$1"
if ! bump_is_valid "$version_bump"; then
  echo "版本类型无效: $version_bump" >&2
  print_usage stderr
  exit 1
fi

if [[ $# -ne 1 ]]; then
  echo "参数数量不正确。" >&2
  print_usage stderr
  exit 1
fi

cd "$REPO_ROOT"
exec uv run python scripts/release/release_core.py "$version_bump"
