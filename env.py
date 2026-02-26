"""Coding environment — services, MCP tools, and scenario definitions."""

import glob
import logging
import os
import shutil
from typing import Any

from sdlc import (
    AgenticGrader,
    BashGrader,
    CodingEnvironment,
    GitHubFileRubricGrader,
    GitHubIssueGrader,
    GitHubLogRubricGrader,
    Grade,
    bash,
    setup_repo,
)
from sdlc.graders import LinearIssueGrader, LinearLogRubricGrader
from sdlc.mcp.coding import CodingService
from sdlc.mcp.github import MockGitHubService
from sdlc.mcp.linear import LinearService
from sdlc.mcp.sentry import SentryService


logger = logging.getLogger(__name__)
MCP_TESTING_MODE = os.environ.get("MCP_TESTING_MODE") in ["1", "true"]


env = CodingEnvironment("coding")

github_service = MockGitHubService()
env.connect_server(github_service.server, prefix="github")

linear_service = LinearService()
env.connect_server(linear_service.server, prefix="linear")

sentry_service = SentryService()
env.connect_server(sentry_service.server, prefix="sentry")

if MCP_TESTING_MODE:
    coding_service = CodingService()
    env.connect_server(coding_service.server)

# ---------------------------------------------------------------------------
# Reset helpers — make scenarios idempotent across repeated runs
# ---------------------------------------------------------------------------

WORKSPACE_BASE = "/home/ubuntu/workspace"
BARE_REPO = "/srv/git/project.git"
GRADING_BASE = "/tmp/grading"


def _reset_environment() -> None:
    """Clean all workspace, bare-repo, and grading artifacts so the next
    scenario starts from a blank slate.  Called at the top of each scenario.
    """
    os.chdir("/mcp_server")
    for pattern in [f"{WORKSPACE_BASE}/*", "/srv/git/*.git", f"{GRADING_BASE}/*"]:
        for path in glob.glob(pattern):
            shutil.rmtree(path, ignore_errors=True)

    for gs in github_service._git_servers.values():
        gs.stop()
    github_service._git_servers.clear()
    github_service._clients.clear()
    github_service._register_client(github_service.client)
    github_service.repo_setup.clear()

    linear_service.data.reload()
    sentry_service.data.reload()


# ---------------------------------------------------------------------------
# Scenario: coding_template  (baseline-test-golden, unit-test grading only)
# ---------------------------------------------------------------------------


@env.scenario(name="coding_template", exclude_tools=["sentry_*", "linear_*", "github_*"])
async def coding_template(
    prompt: str,
    source_repo: str,
    branch_prefix: str,
    test_files: list[str],
    test_command: str = "python -m pytest {test_files} -v",
    workspace_name: str | None = None,
):
    """Barebones scenario for the coding-template 3-branch pattern.

    Mirrors the setup from ``hud-evals/coding-template``:
      ``{branch_prefix}_baseline``  – starting state the agent sees
      ``{branch_prefix}_test``      – hidden test files used for grading
      ``{branch_prefix}_golden``    – correct solution (used for validation)

    No MCP services (GitHub / Linear / Sentry) are configured.
    Grading copies the workspace, injects the hidden test files, and runs
    ``test_command``.

    Args:
        test_command: Shell command with an optional ``{test_files}``
                      placeholder that is expanded at grading time.
                      Examples: ``"python -m pytest {test_files} -v"``
                                ``"yarn test {test_files}"``
                                ``"cargo test"``
    """
    _reset_environment()
    source = f"/home/root/source/{source_repo}"
    workspace = f"{WORKSPACE_BASE}/{workspace_name or source_repo}"
    baseline = f"{branch_prefix}_baseline"
    test_branch = f"{branch_prefix}_test"

    setup_repo(source=source, target=workspace, checkout=baseline, branches=[baseline])

    # ---- prompt ----
    yield prompt

    # ---- grading ----
    grading_dir = f"{GRADING_BASE}/{workspace_name or source_repo}"
    bash(f"mkdir -p {GRADING_BASE} && rm -rf {grading_dir} && cp -r {workspace} {grading_dir}")

    for tf in test_files:
        bash(f"git -C {source} show {test_branch}:{tf} > {grading_dir}/{tf}")

    test_cmd = test_command.format(test_files=" ".join(test_files))
    yield Grade.from_subscores([
        BashGrader.grade(
            weight=1.0,
            command=f"cd {grading_dir} && {test_cmd}",
            timeout=120,
        ),
    ])


# ---------------------------------------------------------------------------
# Scenario: bug_fix  (single-repo, test-file grading)
# ---------------------------------------------------------------------------


@env.scenario(name="bug_fix")
async def bug_fix(
    prompt: str,
    source_repo: str,
    branch_prefix: str,
    test_files: list[str],
    repo_name: str | None = None,
    workspace_name: str | None = None,
    github_data_dir: str | None = None,
    linear_data_dir: str | None = None,
    sentry_data_dir: str | None = None,
    sentry_project: dict | None = None,
    pre_test_commands: list[str] | None = None,
    agentic_criteria: list[dict] | None = None,
    agentic_model: str = "claude-opus-4-6",
    agentic_max_turns: int = 10,
):
    """Generic SDLC bug-fix scenario.

    When ``repo_name`` / ``github_data_dir`` are provided the full
    GitHub + Linear mock workflow is used.  Otherwise a plain
    ``setup_repo`` is enough (e.g. for simple single-file fixes).
    """
    _reset_environment()
    source = f"/home/root/source/{source_repo}"
    workspace = f"{WORKSPACE_BASE}/{workspace_name or source_repo}"
    baseline = f"{branch_prefix}_baseline"
    test_branch = f"{branch_prefix}_test"

    if repo_name and github_data_dir:
        github_service.configure(
            bare_repo_path=BARE_REPO,
            data_dir=f"/mcp_server/data/{github_data_dir}",
            repo_owner="acme-corp",
            repo_name=repo_name,
            default_branch=baseline,
            repo_setup={
                repo_name: [
                    "git config --global --add safe.directory '*'",
                    "su -c \"git config --global --add safe.directory '*'\" ubuntu",
                    "mkdir -p /home/ubuntu",
                    f"rm -rf {BARE_REPO}",
                    "mkdir -p /srv/git",
                    f"git clone --bare {source} {BARE_REPO}",
                    f"git -C {BARE_REPO} branch -D {test_branch} || true",
                    f"git -C {BARE_REPO} branch -D {branch_prefix}_golden || true",
                ],
            },
        )
        github_service.setup_repos()

        bash(f"rm -rf {workspace}")
        bash(f"git clone --branch {baseline} {github_service.repo_url} {workspace}")
        bash(f"chown -R ubuntu:ubuntu {workspace}")

        if linear_data_dir:
            linear_service.configure(data_dir=f"/mcp_server/data/{linear_data_dir}")

        if sentry_data_dir:
            sentry_service.configure(
                data_dir=f"/mcp_server/data/{sentry_data_dir}",
                project=sentry_project,
            )
    else:
        setup_repo(source=source, target=workspace, checkout=baseline, branches=[baseline])

    # ---- prompt ----
    yield prompt

    # ---- grading ----
    if repo_name and github_data_dir:
        grading_dir = f"/tmp/grading/{workspace_name or source_repo}"
        bash(f"mkdir -p /tmp/grading && rm -rf {grading_dir} && git clone {BARE_REPO} {grading_dir}")
        bash(
            f"cd {grading_dir}"
            " && AGENT_REF=$(git for-each-ref --sort=-committerdate"
            " --format='%(refname:short)' refs/remotes/origin"
            " | grep -v HEAD | head -1 | sed 's|^origin/||')"
            " && git checkout \"$AGENT_REF\""
        )

        if pre_test_commands:
            for cmd in pre_test_commands:
                bash(cmd.format(grading_dir=grading_dir))

        for tf in test_files:
            bash(f"git -C {source} diff {baseline}..{test_branch} -- {tf} | git -C {grading_dir} apply")

        yield Grade.from_subscores([
            BashGrader.grade(
                weight=0.8,
                command=f"cd {grading_dir} && python -m pytest {' '.join(test_files)} -v",
                timeout=120,
            ),
            GitHubLogRubricGrader.grade(
                weight=0.2,
                mock_github_client=github_service.client,
                rubric="Did the agent create a pull request with a clear description of the bug fix?",
            ),
        ])
    elif agentic_criteria:
        grading_dir = f"/tmp/grading/{workspace_name or source_repo}"
        bash(f"mkdir -p /tmp/grading && rm -rf {grading_dir} && cp -r {workspace} {grading_dir}")
        for tf in test_files:
            bash(f"git -C {source} diff {baseline}..{test_branch} -- {tf} | git -C {grading_dir} apply")

        grade = Grade.from_subscores(AgenticGrader.grade(
            task_prompt=prompt,
            criteria=agentic_criteria,
            github_service=github_service,
            linear_service=linear_service,
            model=agentic_model,
            max_exploration_turns=agentic_max_turns,
        ))

        for criterion_name, criterion_info in (getattr(grade, "info", None) or {}).items():
            if not isinstance(criterion_info, dict):
                continue
            passed = criterion_info.get("passed")
            icon = "✅" if passed is True else ("❌" if passed is False else "📊")
            action_log = criterion_info.get("action_log", [])
            logger.info(
                "%s %s  passed=%s  turns=%d  reasoning=%s",
                icon, criterion_name, passed, len(action_log),
                (criterion_info.get("reasoning") or "")[:300],
            )
            for i, step in enumerate(action_log, 1):
                cmd = (step.get("command") or "")[:120]
                logger.info("  %d. [%s] %s", i, step.get("action", "?"), cmd)

        yield grade
    else:
        for tf in test_files:
            bash(f"git -C {source} show {test_branch}:{tf} > {workspace}/{tf}")

        yield Grade.from_subscores([
            BashGrader.grade(
                weight=1.0,
                command=f"cd {workspace} && python -m pytest {' '.join(test_files)} -v",
                timeout=120,
            ),
        ])


# ---------------------------------------------------------------------------
# Scenario: bug_fix_linear  (single-repo, GitHub + Linear grading)
# ---------------------------------------------------------------------------


@env.scenario(name="bug_fix_linear")
async def bug_fix_linear(
    prompt: str,
    source_repo: str,
    branch_prefix: str,
    test_files: list[str],
    repo_name: str,
    github_data_dir: str,
    linear_data_dir: str,
    linear_issue_title_contains: str,
    linear_rubric: str,
    workspace_name: str | None = None,
    sentry_data_dir: str | None = None,
    sentry_project: dict | None = None,
    pre_test_commands: list[str] | None = None,
    linear_issue_state_type: str = "completed",
):
    """Bug-fix scenario with GitHub + Linear grading.

    Same setup as ``bug_fix`` with ``repo_name``/``github_data_dir``, but
    adds Linear graders (issue state check + rubric) for tasks where the
    agent is expected to interact with Linear tickets.
    """
    _reset_environment()
    source = f"/home/root/source/{source_repo}"
    workspace = f"{WORKSPACE_BASE}/{workspace_name or source_repo}"
    baseline = f"{branch_prefix}_baseline"
    test_branch = f"{branch_prefix}_test"

    github_service.configure(
        bare_repo_path=BARE_REPO,
        data_dir=f"/mcp_server/data/{github_data_dir}",
        repo_owner="acme-corp",
        repo_name=repo_name,
        default_branch=baseline,
        repo_setup={
            repo_name: [
                "git config --global --add safe.directory '*'",
                "su -c \"git config --global --add safe.directory '*'\" ubuntu",
                "mkdir -p /home/ubuntu",
                f"rm -rf {BARE_REPO}",
                "mkdir -p /srv/git",
                f"git clone --bare {source} {BARE_REPO}",
                f"git -C {BARE_REPO} branch -D {test_branch} || true",
                f"git -C {BARE_REPO} branch -D {branch_prefix}_golden || true",
            ],
        },
    )
    github_service.setup_repos()

    bash(f"rm -rf {workspace}")
    bash(f"git clone --branch {baseline} {github_service.repo_url} {workspace}")
    bash(f"chown -R ubuntu:ubuntu {workspace}")

    linear_service.configure(data_dir=f"/mcp_server/data/{linear_data_dir}")

    if sentry_data_dir:
        sentry_service.configure(
            data_dir=f"/mcp_server/data/{sentry_data_dir}",
            project=sentry_project,
        )

    # ---- prompt ----
    yield prompt

    # ---- grading ----
    grading_dir = f"/tmp/grading/{workspace_name or source_repo}"
    bash(f"mkdir -p /tmp/grading && rm -rf {grading_dir} && git clone {BARE_REPO} {grading_dir}")
    bash(
        f"cd {grading_dir}"
        " && AGENT_REF=$(git for-each-ref --sort=-committerdate"
        " --format='%(refname:short)' refs/remotes/origin"
        " | grep -v HEAD | head -1 | sed 's|^origin/||')"
        " && git checkout \"$AGENT_REF\""
    )

    if pre_test_commands:
        for cmd in pre_test_commands:
            bash(cmd.format(grading_dir=grading_dir))

    for tf in test_files:
        bash(f"git -C {source} diff {baseline}..{test_branch} -- {tf} | git -C {grading_dir} apply")

    yield Grade.from_subscores([
        BashGrader.grade(
            weight=0.6,
            command=f"cd {grading_dir} && python -m pytest {' '.join(test_files)} -v",
            timeout=120,
        ),
        GitHubLogRubricGrader.grade(
            weight=0.1,
            mock_github_client=github_service.client,
            rubric="Did the agent create a pull request with a clear description of the bug fix?",
        ),
        LinearIssueGrader.grade(
            weight=0.1,
            linear_data=linear_service.data,
            title_contains=linear_issue_title_contains,
            state_type=linear_issue_state_type,
        ),
        LinearLogRubricGrader.grade(
            weight=0.2,
            linear_data=linear_service.data,
            rubric=linear_rubric,
        ),
    ])


# ---------------------------------------------------------------------------
# Scenario: bug_fix_multirepo  (N repos, agentic + rubric grading)
# ---------------------------------------------------------------------------


@env.scenario(name="bug_fix_multirepo")
async def bug_fix_multirepo(
    prompt: str,
    primary_repo: dict,
    additional_repos: list[dict],
    repo_owner: str = "acme-corp",
    workspace_name: str | None = None,
    agentic_criteria: list[dict] | None = None,
    agentic_model: str = "claude-opus-4-6",
    agentic_max_turns: int = 15,
    issue_checks: list[dict] | None = None,
    log_rubric_checks: list[dict] | None = None,
    file_rubric_checks: list[dict] | None = None,
):
    """Multi-repo GitHub scenario.

    Sets up multiple independent repos via MockGitHubService, each with
    its own pre-populated GitHub data (issues, PRs, comments, etc.).

    ``primary_repo`` and each entry in ``additional_repos`` are dicts::

        source_repo      – dir name under /home/root/source/
        repo_name        – GitHub repo name to expose
        github_data_dir  – path under data/ for mock GitHub JSON files
        source_branch    – branch in the source to use (default "main")
        default_branch   – branch name to present as default (default "main")
    """
    _reset_environment()
    pr = primary_repo
    source = f"/home/root/source/{pr['source_repo']}"
    workspace = f"{WORKSPACE_BASE}/{workspace_name or pr['repo_name']}"
    default_branch = pr.get("default_branch", "main")
    source_branch = pr.get("source_branch", default_branch)
    bare_path = f"/srv/git/{pr['repo_name']}.git"

    primary_setup = [
        "git config --global --add safe.directory '*'",
        "su -c \"git config --global --add safe.directory '*'\" ubuntu 2>/dev/null || true",
        "mkdir -p /home/ubuntu /srv/git",
        f"rm -rf {bare_path}",
        f"git clone --bare {source} {bare_path}",
    ]
    if source_branch != default_branch:
        primary_setup.extend([
            f"git -C {bare_path} symbolic-ref HEAD refs/heads/{source_branch}",
            f"git -C {bare_path} branch -D {default_branch} 2>/dev/null || true",
            f"git -C {bare_path} branch -m {source_branch} {default_branch}",
        ])

    github_service.configure(
        bare_repo_path=bare_path,
        data_dir=f"/mcp_server/data/{pr['github_data_dir']}",
        repo_owner=repo_owner,
        repo_name=pr["repo_name"],
        default_branch=default_branch,
        repo_setup={pr["repo_name"]: primary_setup},
    )

    extra_clients: dict[str, Any] = {}
    for ar in additional_repos:
        ar_bare = f"/srv/git/{ar['repo_name']}.git"
        ar_source = f"/home/root/source/{ar['source_repo']}"
        ar_default = ar.get("default_branch", "main")
        ar_source_branch = ar.get("source_branch", ar_default)

        c = github_service.add_repo(
            bare_repo_path=ar_bare,
            data_dir=f"/mcp_server/data/{ar['github_data_dir']}",
            repo_owner=ar.get("repo_owner", repo_owner),
            repo_name=ar["repo_name"],
            default_branch=ar_default,
        )
        extra_clients[ar["repo_name"]] = c

        ar_setup = [
            f"rm -rf {ar_bare}",
            f"git clone --bare {ar_source} {ar_bare}",
        ]
        if ar_source_branch != ar_default:
            ar_setup.extend([
                f"git -C {ar_bare} symbolic-ref HEAD refs/heads/{ar_source_branch}",
                f"git -C {ar_bare} branch -D {ar_default} 2>/dev/null || true",
                f"git -C {ar_bare} branch -m {ar_source_branch} {ar_default}",
            ])
        github_service.repo_setup[ar["repo_name"]] = ar_setup

    github_service.setup_repos()

    bash(f"git clone --branch {default_branch} {github_service.repo_url} {workspace}")
    bash(f"chown -R ubuntu:ubuntu {workspace}")

    # ── Prompt ────────────────────────────────────────────────────
    url_lines = "\n".join(
        f"  {k}: {v}" for k, v in github_service.repo_urls.items()
    )
    full_prompt = f"{prompt}\n\nRepo clone URLs:\n{url_lines}"
    yield full_prompt

    # ── Grading ───────────────────────────────────────────────────
    def _client_for(repo_ref: str):
        if repo_ref in ("primary", pr["repo_name"], ""):
            return github_service.client
        return extra_clients.get(repo_ref, github_service.client)

    subscores: list = []

    for ic in (issue_checks or []):
        subscores.append(GitHubIssueGrader.grade(
            weight=ic.get("weight", 0.1),
            mock_github_client=_client_for(ic.get("repo", "primary")),
            state=ic.get("state"),
            title_contains=ic.get("title_contains"),
            body_contains=ic.get("body_contains"),
            labels=ic.get("labels"),
            rubric=ic.get("rubric"),
        ))

    for lc in (log_rubric_checks or []):
        subscores.append(GitHubLogRubricGrader.grade(
            weight=lc.get("weight", 0.1),
            mock_github_client=_client_for(lc.get("repo", "primary")),
            rubric=lc["rubric"],
        ))

    for fc in (file_rubric_checks or []):
        subscores.append(GitHubFileRubricGrader.grade(
            weight=fc.get("weight", 0.1),
            mock_github_client=_client_for(fc.get("repo", "primary")),
            file_path=fc["file_path"],
            branch=fc.get("branch"),
            rubric=fc["rubric"],
        ))

    if agentic_criteria:
        subscores.extend(AgenticGrader.grade(
            task_prompt=full_prompt,
            criteria=agentic_criteria,
            github_service=github_service,
            linear_service=linear_service,
            model=agentic_model,
            max_exploration_turns=agentic_max_turns,
        ))

    grade = Grade.from_subscores(subscores)

    for criterion_name, criterion_info in (getattr(grade, "info", None) or {}).items():
        if not isinstance(criterion_info, dict):
            continue
        passed = criterion_info.get("passed")
        icon = "✅" if passed is True else ("❌" if passed is False else "📊")
        action_log = criterion_info.get("action_log", [])
        logger.info(
            "%s %s  passed=%s  turns=%d  reasoning=%s",
            icon, criterion_name, passed, len(action_log),
            (criterion_info.get("reasoning") or "")[:300],
        )
        for i, step in enumerate(action_log, 1):
            cmd = (step.get("command") or "")[:120]
            logger.info("  %d. [%s] %s", i, step.get("action", "?"), cmd)

    yield grade
