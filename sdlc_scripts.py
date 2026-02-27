"""Convenience wrappers that read .env and pass build args to hud CLI."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

def _load_env() -> dict[str, str]:
    """Load variables from .env file if it exists."""
    env_file = Path(__file__).parent / ".env"
    env: dict[str, str] = {}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


def _build_cmd(hud_command: str) -> list[str]:
    """Build the hud CLI command with build args from .env."""
    dotenv = _load_env()

    # Inject .env values into the process environment so --secret can read them
    for key, value in dotenv.items():
        os.environ.setdefault(key, value)

    cmd = ["hud", hud_command, "."]

    # Pass build secrets (not baked into image layers)
    if os.environ.get("LIB_GITHUB_PAT"):
        cmd.extend(["--secret", "id=LIB_GITHUB_PAT,env=LIB_GITHUB_PAT"])
    if os.environ.get("SOURCE_GITHUB_PAT"):
        cmd.extend(["--secret", "id=SOURCE_GITHUB_PAT,env=SOURCE_GITHUB_PAT"])

    # Pass other build args
    folder_name = os.environ.get("FOLDER_NAME", dotenv.get("FOLDER_NAME", "workspace"))
    cmd.extend(["--build-arg", f"FOLDER_NAME={folder_name}"])

    # Override environment name via ENV_NAME (.env or env var), fallback to pyproject name
    env_name = os.environ.get("ENV_NAME", dotenv.get("ENV_NAME", ""))
    if env_name:
        if hud_command == "deploy":
            cmd.extend(["--name", env_name])
        else:
            cmd.extend(["--tag", env_name])

    cmd.extend(sys.argv[1:])
    return cmd


def _update_sdlc_lib() -> int:
    """Update hud-sdlc-lib to latest commit, returns exit code."""
    pat = _setup_git_auth()
    try:
        result = subprocess.call(["uv", "lock", "--upgrade-package", "hud-sdlc-lib"])
        if result == 0:
            result = subprocess.call(["uv", "sync"])
    finally:
        if pat:
            _teardown_git_auth(pat)
    return result


def dev():
    """Run hud dev --docker with Linear, GitHub, and Sentry frontend ports forwarded."""
    dotenv = _load_env()
    for key, value in dotenv.items():
        os.environ.setdefault(key, value)

    docker_args: list[str] = []
    for env_key in ("LINEAR_FRONTEND_PORT", "GITHUB_FRONTEND_PORT", "SENTRY_FRONTEND_PORT"):
        port = os.environ.get(env_key)
        if port:
            docker_args.extend(["-p", f"{port}:{port}", "-e", f"{env_key}={port}"])

    from sdlc.cli.dev import dev as _dev

    _dev(Path(__file__).parent, docker_args=docker_args)


def build():
    """Update hud-sdlc-lib then run hud build with build args from .env."""
    result = _update_sdlc_lib()
    if result != 0:
        raise SystemExit(result)
    raise SystemExit(subprocess.call(_build_cmd("build")))


def deploy():
    """Run hud deploy with build args from .env."""
    raise SystemExit(subprocess.call(_build_cmd("deploy")))


def _setup_git_auth() -> str | None:
    """Configure git to use LIB_GITHUB_PAT for hud-evals repos. Returns the PAT if set."""
    dotenv = _load_env()
    for key, value in dotenv.items():
        os.environ.setdefault(key, value)

    pat = os.environ.get("LIB_GITHUB_PAT")
    if pat:
        subprocess.run(
            ["git", "config", "--global", "url.https://{}@github.com/hud-evals/.insteadOf".format(pat),
             "https://github.com/hud-evals/"],
            check=True,
        )
    return pat


def _teardown_git_auth(pat: str) -> None:
    """Remove the temporary git credential rewrite."""
    subprocess.run(
        ["git", "config", "--global", "--remove-section",
         "url.https://{}@github.com/hud-evals/".format(pat)],
        check=False,
    )


def update():
    """Update hud-sdlc-lib to latest commit, using LIB_GITHUB_PAT from .env."""
    raise SystemExit(_update_sdlc_lib())


def setup():
    """Run scenario setup for a task against a running hud dev --docker server."""
    from sdlc.cli.setup import setup as _setup

    tasks_by_name, _ = _collect_tasks()
    _setup(tasks_by_name)


def _collect_tasks() -> tuple[dict[str, Any], dict[str, str]]:
    """Import tasks package and return task objects + task IDs.

    Returns:
      - name -> Task object mapping
      - name -> task_id mapping from Task.slug
    """
    project_root = str(Path(__file__).parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    import tasks as tasks_pkg

    raw_tasks = getattr(tasks_pkg, "tasks", {})
    tasks_by_name = raw_tasks if isinstance(raw_tasks, dict) else {}
    if not tasks_by_name:
        print("No Task objects found in tasks/ subpackages.")
    raw = getattr(tasks_pkg, "task_ids", {})
    if not isinstance(raw, dict):
        return tasks_by_name, {}
    task_ids = {
        str(folder_name): str(task_id)
        for folder_name, task_id in raw.items()
        if isinstance(folder_name, str) and isinstance(task_id, str)
    }
    return tasks_by_name, task_ids


def new_task():
    """Scaffold a new task directory."""
    from sdlc.cli.new_task import new_task as _new_task

    _new_task(Path(__file__).parent / "tasks")


def sync_tasks():
    """Sync local task definitions to a platform taskset via API-key endpoints."""
    from sdlc.cli.sync_tasks import sync_tasks as _sync

    tasks, task_ids = _collect_tasks()
    dotenv = _load_env()
    _sync(tasks, task_ids, env_name=dotenv.get("ENV_NAME", ""), taskset=dotenv.get("TASKSET_NAME", ""))


def generate_golden():
    """Generate a golden.patch file from a GitHub diff between two branches."""
    from sdlc.cli.generate_golden import generate_golden as _gen

    dotenv = _load_env()
    for key, value in dotenv.items():
        os.environ.setdefault(key, value)
    _gen(Path(__file__).parent / "tasks")


def validate():
    """Run baseline-fail + golden replay validation.

    Usage: validate [task_name] [--url URL]

    If task_name is given, validates only tasks whose directory name
    contains that string.  Otherwise validates all tasks.
    """
    from sdlc.cli.validate import validate as _validate

    args = sys.argv[1:]

    url = None
    if "--url" in args:
        idx = args.index("--url")
        url = args[idx + 1]
        del args[idx : idx + 2]

    task_name = next((a for a in args if not a.startswith("-")), None)

    all_tasks, _ = _collect_tasks()
    if not all_tasks:
        raise SystemExit(1)

    if task_name:
        matched = {k: v for k, v in all_tasks.items() if task_name in k}
        if not matched:
            print(f"No tasks matching '{task_name}'")
            print(f"Available: {', '.join(sorted(all_tasks))}")
            raise SystemExit(1)
        tasks = list(matched.values())
    else:
        tasks = list(all_tasks.values())

    _validate(tasks, url=url, project_dir=Path(__file__).parent, restart_between_tasks=False)


def init():
    """Bootstrap: set up git auth, run uv lock + uv sync, then tear down auth.

    Callable without a lockfile via: python3 sdlc_scripts.py init
    """
    pat = _setup_git_auth()
    try:
        result = subprocess.call(["uv", "lock"])
        if result == 0:
            result = subprocess.call(["uv", "sync"])
    finally:
        if pat:
            _teardown_git_auth(pat)
    raise SystemExit(result)


if __name__ == "__main__":
    commands = {"init": init}
    cmd = sys.argv[1] if len(sys.argv) > 1 else None
    if cmd not in commands:
        print(f"Usage: python3 {Path(__file__).name} <{'|'.join(commands)}>")
        raise SystemExit(1)
    sys.argv = sys.argv[1:]  # shift so the subcommand sees its own args
    commands[cmd]()
