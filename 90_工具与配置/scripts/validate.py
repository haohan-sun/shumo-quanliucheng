from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

TOOLS_ROOT = Path(__file__).resolve().parents[1]
ROOT = TOOLS_ROOT.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the project validation suite.")
    parser.add_argument("--with-tests", action="store_true")
    parser.add_argument("--submission", action="store_true")
    args = parser.parse_args()
    commands = [
        [sys.executable, str(TOOLS_ROOT / "scripts" / "doctor.py")],
        [sys.executable, str(TOOLS_ROOT / "scripts" / "verify_structure.py")],
        [sys.executable, str(TOOLS_ROOT / "scripts" / "validate_contracts.py")],
    ]
    if args.submission:
        commands.append(
            [sys.executable, str(TOOLS_ROOT / "scripts" / "compliance.py"), "--submission"]
        )
    if args.with_tests:
        commands.append([sys.executable, "-m", "pytest"])
    for command in commands:
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode:
            return result.returncode
    print("validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
