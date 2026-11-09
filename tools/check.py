import subprocess
import sys

CHECKS: tuple[tuple[str, list[str]], ...] = (
    ("ruff check", [sys.executable, "-m", "ruff", "check", "--no-cache", "src", "tests"]),
    (
        "ruff format",
        [sys.executable, "-m", "ruff", "format", "--check", "--no-cache", "src", "tests"],
    ),
    ("mypy --strict", [sys.executable, "-m", "mypy"]),
    ("unittest", [sys.executable, "-m", "unittest", "discover", "-s", "tests"]),
)


def main() -> int:
    failed = []
    for name, command in CHECKS:
        print(f"== {name}", flush=True)
        if subprocess.run(command, check=False).returncode != 0:
            failed.append(name)
    print("ALL CHECKS PASSED" if not failed else f"FAILED: {', '.join(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
