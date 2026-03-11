from pathlib import Path

from hud.types import MCPToolCall
from env import bug_fix_linear

WORKSPACE = "/home/ubuntu/workspace/wireguard-go"

task = bug_fix_linear.task(
    prompt=(
        "You are an on-call engineer for the Networking team. "
        "Production metrics show that the WireGuard VPN gateway is accepting slightly more "
        "handshake-initiation packets per source IP than the rate limiter should allow. "
        "Under sustained load, this lets attackers push ~20%% more CPU-bound handshake work "
        "onto the gateway than intended.\n\n"
        "Check the GitHub issues on acme-corp/wireguard-go for details from the SRE team. "
        "The code is available locally at /home/ubuntu/workspace/wireguard-go.\n\n"
        "Your job:\n"
        "1. Investigate the GitHub issues and the ratelimiter package to find the root cause\n"
        "2. Fix the bug\n"
        "3. Commit your changes to a new branch and push to origin\n"
        "4. Create a pull request using the GitHub tools\n"
        "5. Create a Linear ticket (team: Networking) documenting your diagnosis and fix\n"
        "6. Mark your Linear ticket as Done\n"
    ),
    source_repo="wireguard-go",
    repo_name="wireguard-go",
    workspace_name="wireguard-go",
    branch_prefix="ratelimiter_bug",
    test_files=["ratelimiter/ratelimiter_burst_test.go"],
    github_data_dir="wireguard_ratelimiter_task/wg_github_data",
    linear_data_dir="wireguard_ratelimiter_task/wg_linear_data",
    linear_issue_title_contains="ratelimiter",
    linear_rubric=(
        "Did the agent create a Linear ticket with a clear diagnosis of the rate limiter "
        "burst bug and document the fix? Did the agent mark the ticket as Done?"
    ),
    pre_test_commands=[
        "cd {grading_dir} && go mod download 2>/dev/null || true",
    ],
    test_command="cd {grading_dir} && go test ./ratelimiter/ -run TestRatelimiterBurst -v",
)
task.slug = "wireguard_ratelimiter_bug"
task.validation = [
    MCPToolCall(name="bash", arguments={
        "command": f"cd {WORKSPACE} && git apply <<'GOLDEN_PATCH'\n"
        + (Path(__file__).parent / "golden.patch").read_text()
        + "GOLDEN_PATCH",
    }),
    MCPToolCall(name="bash", arguments={
        "command": f"cd {WORKSPACE}"
        " && git checkout -b fix/ratelimiter-initial-burst"
        " && git add -A"
        " && git commit -m 'fix: correct initial token count in ratelimiter to prevent burst overshoot'"
        " && git push origin fix/ratelimiter-initial-burst",
    }),
    MCPToolCall(name="github_create_pull_request", arguments={
        "owner": "acme-corp",
        "repo": "wireguard-go",
        "title": "fix: correct initial token count in ratelimiter to prevent burst overshoot",
        "body": (
            "## Summary\n\n"
            "Fixed an off-by-one bug in the rate limiter that allowed "
            "`packetsBurstable + 1` packets in the initial burst window instead "
            "of `packetsBurstable`.\n\n"
            "**Root cause:** When a new `RatelimiterEntry` is created for a "
            "previously-unseen source IP, `Allow()` returns `true` immediately "
            "(counting as one allowed packet) and initialises `entry.tokens` to "
            "`maxTokens`. On the next call the full `maxTokens` budget is still "
            "available, so `packetsBurstable` *more* packets are allowed before "
            "the bucket drains -- giving a total burst of `packetsBurstable + 1`.\n\n"
            "**Fix:** Initialise `entry.tokens` to `maxTokens - packetCost` so "
            "that the implicit first-packet allowance is accounted for.\n\n"
            "Fixes #78, #82"
        ),
        "head": "fix/ratelimiter-initial-burst",
        "base": "ratelimiter_bug_baseline",
    }),
]
