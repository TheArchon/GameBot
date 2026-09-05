from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


class UpdateError(RuntimeError):
    """Raised when a safe self-update cannot be completed."""


@dataclass(frozen=True)
class UpdateResult:
    changed: bool
    old_commit: str
    new_commit: str
    branch: str
    message: str


def _run(args: list[str], cwd: Path, timeout: int = 180) -> str:
    try:
        proc = subprocess.run(
            args,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise UpdateError(f"Command failed: {' '.join(args)}") from exc
    output = proc.stdout.strip()
    if proc.returncode != 0:
        raise UpdateError(output[-1500:] or f"Command exited with code {proc.returncode}.")
    return output


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def update_and_validate(root: Path | None = None) -> UpdateResult:
    """Pull the configured Git branch while safely preserving the VPS .env."""
    root = (root or project_root()).resolve()

    if not (root / ".git").is_dir():
        raise UpdateError("This installation is not a Git working tree.")

    branch = os.getenv("UPDATE_BRANCH", "").strip()
    if not branch:
        branch = _run(["git", "branch", "--show-current"], root, 30)

    if not branch:
        raise UpdateError("Could not determine the current Git branch.")

    status = _run(["git", "status", "--porcelain"], root, 30)

    env_backup = None
    env_file = root / ".env"

    if status:
        changes = []

        for line in status.splitlines():
            if len(line) >= 4:
                path = line[3:].strip()

                # Handle quoted Git paths.
                if path.startswith('"') and path.endswith('"'):
                    path = path[1:-1]

                # Handle rename/copy status paths.
                if " -> " in path:
                    path = path.split(" -> ", 1)[-1].strip()

                changes.append(path)

        unexpected = [path for path in changes if path != ".env"]

        if unexpected:
            raise UpdateError(
                "Working tree contains local changes outside .env: "
                + ", ".join(unexpected)
            )

        if env_file.exists():
            import shutil
            import tempfile

            fd, backup_path = tempfile.mkstemp(
                prefix="gamebot-env-",
                suffix=".backup",
            )
            os.close(fd)

            env_backup = Path(backup_path)
            shutil.copy2(env_file, env_backup)

            _run(["git", "restore", "--", ".env"], root, 30)

    def restore_env() -> None:
        if env_backup and env_backup.exists():
            import shutil

            shutil.copy2(env_backup, env_file)
            env_backup.unlink(missing_ok=True)

    try:
        old_commit = _run(["git", "rev-parse", "HEAD"], root, 30)

        _run(
            ["git", "fetch", "origin", branch, "--prune"],
            root,
            180,
        )

        _run(
            ["git", "pull", "--ff-only", "origin", branch],
            root,
            180,
        )

        new_commit = _run(["git", "rev-parse", "HEAD"], root, 30)

        if new_commit == old_commit:
            restore_env()

            return UpdateResult(
                False,
                old_commit,
                new_commit,
                branch,
                "Already up to date.",
            )

        try:
            requirements = root / "requirements.txt"

            install_deps = os.getenv(
                "UPDATE_INSTALL_DEPS",
                "1",
            ).lower() not in {"0", "false", "no"}

            if (
                install_deps
                and requirements.exists()
                and requirements.read_text(
                    encoding="utf-8"
                ).strip()
            ):
                _run(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        "-r",
                        str(requirements),
                    ],
                    root,
                    600,
                )

            _run(
                [
                    sys.executable,
                    "-m",
                    "compileall",
                    "-q",
                    "app",
                    "tests",
                    "scripts",
                ],
                root,
                120,
            )

            if os.getenv(
                "UPDATE_RUN_TESTS",
                "1",
            ).lower() not in {"0", "false", "no"}:
                _run(
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        "-q",
                    ],
                    root,
                    600,
                )

        except Exception as exc:
            try:
                _run(
                    ["git", "reset", "--hard", old_commit],
                    root,
                    120,
                )
            finally:
                restore_env()

            raise UpdateError(
                f"Update validation failed; reverted to "
                f"{old_commit[:12]}. {exc}"
            ) from exc

        restore_env()

        return UpdateResult(
            True,
            old_commit,
            new_commit,
            branch,
            f"Updated from {old_commit[:12]} to "
            f"{new_commit[:12]} on {branch}.",
        )

    except Exception:
        restore_env()
        raise

def restart_process() -> None:
    """Replace the running process so the freshly pulled code is loaded."""
    os.execv(sys.executable, [sys.executable, "-m", "app"])
