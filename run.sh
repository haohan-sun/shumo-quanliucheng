#!/usr/bin/env bash
# Project CLI (POSIX launcher).
#
# Thin wrapper: all command behaviour lives in <tool root>/scripts/cli.py so that
# Windows and POSIX runs cannot drift apart.  `setup` is handled before the
# interpreter check and delegated to ./setup.sh, so the first command a new user
# runs works before .venv exists.
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_dir"

tools_root="$(find . -maxdepth 1 -type d -name '90_*' -print -quit)"
if [ -z "$tools_root" ]; then
    echo "run: FAIL" >&2
    echo "  cannot locate the tool root (a '90_*' directory) in $script_dir" >&2
    exit 2
fi

if [ "$#" -eq 0 ]; then
    set -- help
fi

case "$1" in
    setup|bootstrap)
        shift
        if [ ! -f ./setup.sh ]; then
            echo "run: FAIL" >&2
            echo "  setup.sh is missing next to run.sh; cannot provision the environment." >&2
            exit 2
        fi
        exec ./setup.sh "$@"
        ;;
esac

python=""
for candidate in .venv/bin/python .venv/Scripts/python.exe; do
    if [ -x "$candidate" ]; then
        python="$candidate"
        break
    fi
done

if [ -z "$python" ]; then
    echo "Project Python is missing." >&2
    echo "  expected: $script_dir/.venv/bin/python" >&2
    echo "" >&2
    echo "Run the setup step first:" >&2
    echo "  ./run.sh setup" >&2
    echo "  or          :  ./setup.sh" >&2
    exit 2
fi

export UV_CACHE_DIR="${UV_CACHE_DIR:-$script_dir/$tools_root/.cache/uv}"
export PYTHONDONTWRITEBYTECODE=1
# Force UTF-8 streams: this repository prints non-ASCII paths.
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

exec "$python" "$tools_root/scripts/cli.py" "$@"
