#!/usr/bin/env bash
# Create or refresh the project virtual environment (POSIX entry point).
#
# Idempotent: an already-correct .venv is detected and reused.  Finds a Python
# interpreter that satisfies the range declared in pyproject.toml, creates
# .venv, installs required dependencies, and runs the environment doctor.
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_dir"

if [ ! -f pyproject.toml ]; then
    echo "setup: FAIL" >&2
    echo "  pyproject.toml not found next to $0; run this script from the repository." >&2
    exit 1
fi

tools_root="$(find . -maxdepth 1 -type d -name '90_*' -print -quit)"
if [ -z "$tools_root" ]; then
    echo "setup: FAIL" >&2
    echo "  cannot locate the tool root (a '90_*' directory) in $script_dir" >&2
    exit 1
fi

find_python() {
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1; then
            if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3, 11) else 1)' 2>/dev/null; then
                command -v "$candidate"
                return 0
            fi
        fi
    done
    return 1
}

if ! python_bin="$(find_python)"; then
    echo "setup: FAIL" >&2
    echo "  no Python 3.11+ interpreter found on PATH" >&2
    echo "  this project requires: $(grep -m1 'requires-python' pyproject.toml | tr -d ' ')" >&2
    echo "  install a supported Python 3 and re-run ./setup.sh" >&2
    exit 1
fi

exec "$python_bin" "$tools_root/scripts/bootstrap.py" "$@"
