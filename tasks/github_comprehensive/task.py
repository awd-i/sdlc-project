from hud.types import MCPToolCall
from env import bug_fix_multirepo

WORKSPACE = "/home/ubuntu/workspace/server_app"

task = bug_fix_multirepo.task(
    prompt=(
        "You have access to 3 GitHub repositories owned by acme-corp:\n"
        "  1. server-app   -- Python HTTP server with Flask REST API\n"
        "  2. settings-api -- Settings management API v2\n"
        "  3. hud-sdk      -- HUD Python SDK for AI evaluation\n\n"
        "All three repos have pre-existing issues, pull requests, comments, "
        "reviews, and milestones data. Your job is to comprehensively test "
        "this multi-repo GitHub environment through 5 phases.\n\n"
        "IMPORTANT debugging mindset: if any tool call returns unexpected "
        "results (empty, errors, wrong data), do NOT just move on. "
        "Investigate: retry with different parameters, try the equivalent "
        "list tool, try simpler queries, and report exactly what you tried.\n\n"
        "KNOWN LIMITATIONS (do not waste time on these):\n"
        "  - There is no list_milestones tool. Milestones exist in data "
        "but cannot be listed via the API.\n"
        "  - github_get_pull_request_files on pre-existing merged PRs returns empty "
        "(only works on PRs you create yourself).\n\n"
        # ── Phase 1: Tool coverage ─────────────────────────────────────
        "=== PHASE 1: TOOL COVERAGE ===\n\n"
        "Call EVERY available GitHub tool at least once. For each tool, "
        "report what you called and what it returned. Specifically:\n\n"
        "READ tools (call all of these):\n"
        "  - github_get_file_contents: read root directory of each repo\n"
        "  - github_list_issues: list issues on all 3 repos (server-app "
        "should have 5, settings-api 4, hud-sdk 3)\n"
        "  - github_get_issue: get details of server-app issue #1\n"
        "  - github_list_pull_requests: list PRs on all 3 repos\n"
        "  - github_get_pull_request: get details of server-app PR #7\n"
        "  - github_get_pull_request_reviews: check reviews on server-app PR #7 "
        "(should show CHANGES_REQUESTED by alice-dev)\n"
        "  - github_get_pull_request_comments: check review comments on any PR\n"
        "  - github_get_pull_request_status: check status on any PR\n"
        "  - github_list_commits: list recent commits on server-app\n"
        "  - github_search_repositories: search for all available repos\n"
        "  - github_search_users: search for 'agent' (should find agent-bot)\n"
        "  - github_search_issues: search for 'Login' (should match "
        "server-app issue #1 title). Also try 'validation' and 'CORS'. "
        "NOTE: search matches title/body TEXT, not labels.\n"
        "  - github_search_code: search for 'import' across all repos\n\n"
        "WRITE tools (exercise all of these in later phases):\n"
        "  github_create_branch, github_create_or_update_file, github_push_files, "
        "github_create_issue, github_update_issue, github_add_issue_comment, "
        "github_create_pull_request, github_create_pull_request_review, "
        "github_merge_pull_request, github_fork_repository, github_create_repository\n\n"
        "Also try: github_update_pull_request_branch on an open PR, and "
        "github_get_pull_request_files on a PR you create.\n\n"
        # ── Phase 2: SDLC bug-fix workflow ─────────────────────────────
        "=== PHASE 2: SDLC BUG-FIX WORKFLOW ===\n\n"
        "Perform a realistic end-to-end bug-fix workflow on server-app:\n\n"
        "1. Read issue #1 ('Login endpoint returns 500 on empty password') "
        "to understand the bug from its description and comments.\n"
        "2. Create a branch 'fix/login-empty-password' from main.\n"
        "3. Read the existing source code with github_get_file_contents to find "
        "the relevant file (the issue mentions auth.py).\n"
        "4. Create or update a file with a fix (add input validation).\n"
        "5. Open a PR titled 'Fix: validate empty password in login' "
        "with a body that references issue #1 (e.g. 'Closes #1').\n"
        "6. Submit a review (APPROVE) on your own PR.\n"
        "7. Merge the PR.\n"
        "8. Verify: use github_get_file_contents on the default branch to "
        "confirm your fix is there. Use github_get_pull_request to confirm "
        "the PR is merged. Use github_list_commits to see the merge commit.\n"
        "9. Close issue #1 using github_update_issue with state='closed'.\n"
        "10. Verify issue #1 is now closed via github_get_issue.\n\n"
        # ── Phase 3: Git bash + MCP interop ────────────────────────────
        "=== PHASE 3: GIT BASH + MCP INTEROP ===\n\n"
        "Test that bash git commands and MCP tools see the same state:\n\n"
        "1. BASH → MCP: In your workspace (which is a git clone of "
        "server-app), use bash to create a file, git add, git commit, "
        "and git push to a new branch. Then use github_get_file_contents via "
        "the MCP tool to read that file from the pushed branch. "
        "Confirm the content matches what you wrote.\n\n"
        "2. MCP → BASH: Use github_create_branch + github_create_or_update_file via "
        "MCP to create a file on settings-api on a new branch. Then "
        "use bash: git clone the settings-api repo (the clone URL is "
        "in the repo info), checkout that branch, and cat the file. "
        "Confirm the content matches.\n\n"
        "3. Use bash 'git log' on the server-app workspace to see "
        "commits from your Phase 2 merge. Confirm the merge commit "
        "from the MCP github_merge_pull_request appears in the git log.\n\n"
        "4. BASH CODE EDIT: In your server-app workspace, use bash to "
        "edit an existing file (e.g. use sed or echo >> to add a comment "
        "or modify a string in server.py), then git add, commit, and "
        "push to a new branch. Use github_get_file_contents to read that file "
        "from the branch and confirm your edit is visible.\n\n"
        "5. BASH ON SECONDARY REPO: Clone settings-api via bash, edit "
        "an existing Python file (e.g. add a docstring to app.py with "
        "sed), commit, push to a new branch. Verify the edit via "
        "github_get_file_contents on that branch.\n\n"
        # ── Phase 4: Cross-repo migration ──────────────────────────────
        "=== PHASE 4: CROSS-REPO MIGRATION ===\n\n"
        "Migrate data between repos:\n\n"
        "1. ISSUE MIGRATION: Read all open issues from settings-api "
        "using github_list_issues. For each open issue, create a copy "
        "on hud-sdk with the title prefixed by '[migrated] '. "
        "Verify by listing issues on hud-sdk afterwards -- the migrated "
        "issues should appear alongside the original ones.\n\n"
        "2. CODE MIGRATION: Use github_get_file_contents to read a Python file "
        "from settings-api (e.g. the main app file). Then push that "
        "same file to a new branch on hud-sdk using github_push_files. Open "
        "a PR on hud-sdk for the migrated code. Use "
        "github_get_pull_request_files to verify the file appears in the diff.\n\n"
        "3. CROSS-REFERENCE: Create an issue on server-app titled "
        "'Track: code migrated to hud-sdk' with a body that references "
        "the hud-sdk PR number you just created.\n\n"
        # ── Phase 5: Search & edge cases ───────────────────────────────
        "=== PHASE 5: SEARCH & EDGE CASES ===\n\n"
        "1. Use github_search_issues to find issues YOU created in "
        "earlier phases. Search for 'migrated' -- it should find the "
        "issues you copied to hud-sdk.\n"
        "2. Use github_search_code to find the file you migrated from "
        "settings-api to hud-sdk.\n"
        "3. Use github_fork_repository to fork hud-sdk.\n"
        "4. Use github_create_repository to create a brand new repo.\n"
        "5. List issues with state='closed' on server-app -- verify "
        "issue #1 (which you closed in Phase 2) appears.\n"
        "6. List issues with state='all' on each repo and confirm "
        "total = open + closed.\n"
        "7. Try reading a file that doesn't exist (expect an error).\n\n"
        # ── Report ────────────────────────────────────────────────────
        "=== FINAL REPORT ===\n\n"
        "Provide a structured report:\n"
        "- Phase 1: which tools worked, which didn't, any surprises\n"
        "- Phase 2: each step of the SDLC workflow and its outcome\n"
        "- Phase 3: for each interop test, did bash and MCP agree?\n"
        "- Phase 4: how many issues migrated, code migration outcome\n"
        "- Phase 5: search results and edge case outcomes\n"
        "- Tool call inventory: every distinct tool name and call count\n"
        "- Overall: fully functional, partially functional, or broken?"
    ),
    primary_repo={
        "source_repo": "coding-template-sample",
        "repo_name": "server-app",
        "github_data_dir": "github_comprehensive_task/github_data/server_app",
        "source_branch": "server_fix_baseline",
        "default_branch": "main",
    },
    additional_repos=[
        {
            "source_repo": "coding-template-sample",
            "repo_name": "settings-api",
            "github_data_dir": "github_comprehensive_task/github_data/settings_v2",
            "source_branch": "settings_v2_baseline",
            "default_branch": "main",
        },
        {
            "source_repo": "sdlc-tasks-data",
            "repo_name": "hud-sdk",
            "github_data_dir": "github_comprehensive_task/github_data/hud_sdk",
            "source_branch": "openai_schema_baseline",
            "default_branch": "main",
        },
    ],
    workspace_name="server_app",
    agentic_max_turns=40,
    issue_checks=[
        {
            "repo": "hud-sdk",
            "state": "open",
            "title_contains": "[migrated]",
            "weight": 0.1,
        },
        {
            "repo": "server-app",
            "state": "open",
            "title_contains": "Track: code migrated",
            "weight": 0.05,
        },
    ],
    log_rubric_checks=[
        {
            "repo": "primary",
            "weight": 0.1,
            "rubric": (
                "SDLC WORKFLOW: Did the agent do a full bug-fix lifecycle "
                "on server-app? Check for: read issue → create branch → "
                "read source → fix file → open PR referencing the issue → "
                "review → merge → verify file on default branch → close "
                "issue. Award full credit for the complete chain with "
                "verification. Award 0.5 if merge happened but issue "
                "wasn't closed or file wasn't verified."
            ),
        },
        {
            "repo": "hud-sdk",
            "weight": 0.05,
            "rubric": (
                "CROSS-REPO MIGRATION: Did the agent migrate issues from "
                "settings-api to hud-sdk (with '[migrated]' prefix) AND "
                "push code from settings-api to hud-sdk on a branch with "
                "a PR? Award full credit for both. Award 0.5 for one."
            ),
        },
    ],
    file_rubric_checks=[],
    agentic_criteria=[
        {
            "rubric": (
                "TOOL COVERAGE: Did the agent call a wide range of "
                "GitHub tools? Check the action log for:\n"
                "READ: github_get_file_contents, github_list_issues, github_get_issue, "
                "github_list_pull_requests, github_get_pull_request, "
                "github_get_pull_request_reviews, github_list_commits, "
                "github_search_issues, github_search_code, github_search_repositories\n"
                "WRITE: github_create_branch, github_create_or_update_file, github_push_files, "
                "github_create_issue, github_update_issue, github_add_issue_comment, "
                "github_create_pull_request, github_create_pull_request_review, "
                "github_merge_pull_request\n"
                "Award full credit if 15+ distinct tool names appear. "
                "Award 0.5 for 10-14 distinct tools."
            ),
            "weight": 0.25,
        },
        {
            "rubric": (
                "BASH + MCP INTEROP: Did the agent test consistency "
                "between bash git commands and MCP tools?\n"
                "- Created or edited a file via bash (add, commit, push) "
                "then read it back via github_get_file_contents MCP tool\n"
                "- OR created a file via MCP tool then verified it via "
                "bash git clone/cat\n"
                "- OR used bash to EDIT an existing source file (e.g. "
                "server.py or app.py with sed/echo), pushed, and "
                "verified the edit via github_get_file_contents\n"
                "- OR used bash git log to verify MCP merge commits\n"
                "Award full credit for at least 3 interop tests "
                "including at least 1 that edits existing code. "
                "Award 0.5 for 2 tests without code editing."
            ),
            "weight": 0.15,
        },
        {
            "rubric": (
                "CROSS-REPO OPERATIONS: Did the agent move data "
                "between repos?\n"
                "- Read issues from one repo and created copies on another\n"
                "- Read code from one repo and pushed it to another\n"
                "- Created cross-references between repos (issue body "
                "mentioning another repo's PR)\n"
                "Award full credit for issue migration + code migration. "
                "Award 0.5 for only one of these."
            ),
            "weight": 0.15,
        },
        {
            "rubric": (
                "SEARCH TESTING: Did the agent use search tools "
                "effectively?\n"
                "- Used github_search_issues with terms that match "
                "issue titles (e.g. 'Login', 'validation', 'migrated')\n"
                "- Used github_search_code with at least 1 query that returns "
                "real file paths\n"
                "- Used github_search_repositories or github_search_users\n"
                "- When search returned 0, investigated by listing data "
                "and retrying with different terms\n"
                "Award full credit for 3+ search calls with real "
                "results. Award 0.5 for some search attempts."
            ),
            "weight": 0.15,
        },
    ],
)
task.slug = "github_comprehensive"
