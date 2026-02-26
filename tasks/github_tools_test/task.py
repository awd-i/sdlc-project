from env import bug_fix

task = bug_fix.task(
    prompt=(
        "You are testing the GitHub integration. Your goal is to exercise ALL "
        "available GitHub tools to verify the mock environment works correctly.\n\n"
        "The repository is owner: acme-corp, repo: server-app.\n\n"
        "Please perform the following steps IN ORDER, using the GitHub MCP tools:\n\n"
        "--- READ OPERATIONS ---\n"
        "1. Use github_get_file_contents to read the root directory of the repo (path: '')\n"
        "2. Use github_get_file_contents to read the first file you find\n"
        "3. Use github_list_commits to see recent commits\n"
        "4. Use github_list_issues to see open issues (owner: acme-corp, repo: server-app)\n"
        "5. Use github_get_issue to read issue #1 in detail\n"
        "6. Use github_search_code to search for 'def ' in the repo "
        "(q: 'def  repo:acme-corp/server-app')\n"
        "7. Use github_search_issues to search for issues with query 'test'\n"
        "8. Use github_search_users to search for user 'agent'\n"
        "9. Use github_search_repositories to search for 'server'\n"
        "10. Use github_list_pull_requests to list PRs\n\n"
        "--- WRITE OPERATIONS ---\n"
        "11. Use github_create_branch to create a branch called 'feature/tools-test' "
        "from the default branch\n"
        "12. Use github_create_or_update_file to create a new file 'test-file.txt' with "
        "content 'Hello from tools test' on branch 'feature/tools-test' with "
        "message 'Add test file'\n"
        "13. Use github_get_file_contents to verify 'test-file.txt' exists on branch "
        "'feature/tools-test' — confirm the content matches what you wrote\n"
        "14. Use github_push_files to push two files at once to branch 'feature/tools-test': "
        "'file-a.txt' with content 'File A content' and 'file-b.txt' with content "
        "'File B content', commit message 'Add two files'\n"
        "15. Use github_get_file_contents to verify BOTH file-a.txt and file-b.txt exist "
        "on branch 'feature/tools-test'\n"
        "16. Use github_create_issue to create a new issue titled 'Tools test issue' with "
        "body 'Created by tools test'\n"
        "17. Use github_update_issue to add the label 'verified' to the issue you "
        "just created\n"
        "18. Use github_get_issue to re-read the issue and verify the label was added\n"
        "19. Use github_add_issue_comment to comment 'Test comment' on issue #1\n"
        "20. Use github_create_pull_request to create a PR from 'feature/tools-test' to "
        "the default branch titled 'Tools test PR'\n"
        "21. Use github_get_pull_request to read the PR you just created\n"
        "22. Use github_get_pull_request_files to see files changed in the PR — verify "
        "that test-file.txt, file-a.txt, and file-b.txt all appear\n"
        "23. Use github_get_pull_request_status to check the PR's combined status\n"
        "24. Use github_get_pull_request_comments to list PR review comments\n"
        "25. Use github_get_pull_request_reviews to list PR reviews (should be empty)\n"
        "26. Use github_create_pull_request_review to submit a review on the PR with "
        "event 'COMMENT' and body 'Looks good'\n"
        "27. Use github_get_pull_request_reviews again to verify your review appears\n"
        "28. Use github_merge_pull_request to merge the PR (merge_method: 'merge')\n"
        "29. Use github_get_pull_request again to verify the PR is now merged\n\n"
        "--- EXTRA VERIFICATION ---\n"
        "30. Use github_get_file_contents to verify 'test-file.txt' is now on the "
        "default branch (after merge) — this proves the merge actually worked\n"
        "31. Use github_list_commits on the default branch — verify there are more "
        "commits now than at the start\n"
        "32. Use github_create_repository to create a new repo called 'test-repo' with "
        "description 'Test repository'\n"
        "33. Use github_fork_repository to fork acme-corp/server-app\n"
        "34. Use github_update_pull_request_branch on the PR (even though it's merged, "
        "verify the tool responds)\n\n"
        "--- EDGE CASE EXPLORATION ---\n"
        "Now go beyond the basic flow. Try to find edge cases and verify the "
        "environment handles them correctly:\n"
        "35. Use github_create_or_update_file to UPDATE 'test-file.txt' (overwrite with "
        "new content 'Updated content') on the default branch — verify the SHA "
        "changed from the original\n"
        "36. Use github_get_file_contents to confirm the update took effect\n"
        "37. Use github_list_issues with state='all' — verify both the original "
        "and your new issue appear\n"
        "38. Use github_update_issue to close the issue you created (state: 'closed')\n"
        "39. Use github_get_issue to verify the issue is now closed\n"
        "40. Use github_search_issues with a query that should match your issue\n"
        "41. Use github_search_code to search for 'Updated content' — verify the updated "
        "file is found\n"
        "42. Use github_create_branch to create another branch 'feature/edge-test'\n"
        "43. Use github_push_files to push a file to 'feature/edge-test'\n"
        "44. Use github_create_pull_request to create a second PR\n"
        "45. Use github_get_pull_request_files on the second PR\n\n"
        "After completing all steps, provide a DETAILED summary:\n"
        "- List every tool name you called\n"
        "- For each tool, note whether it succeeded or failed\n"
        "- Highlight any unexpected behavior or edge cases you found\n"
        "- Confirm whether write operations persisted correctly (e.g., created "
        "files were readable, merged PRs stayed merged, issue labels stuck)\n"
        "- Rate the overall health of the mock environment (fully functional / "
        "partially functional / broken)"
    ),
    source_repo="coding-template-sample",
    repo_name="server-app",
    workspace_name="server_repo",
    branch_prefix="server_fix",
    test_files=["test_server.py"],
    github_data_dir="github_tools_test_task/tools_github_data",
    agentic_criteria=[
        {
            "rubric": (
                "Check the GitHub action log. Did the agent successfully call ALL "
                "of the following read tools: github_get_file_contents, github_list_commits, "
                "github_list_issues, github_get_issue, github_search_code, github_search_issues, "
                "github_search_users, github_search_repositories, github_list_pull_requests, "
                "github_get_pull_request, github_get_pull_request_files, github_get_pull_request_status, "
                "github_get_pull_request_comments, github_get_pull_request_reviews? "
                "Award full credit if at least 12 of these 14 were called."
            ),
            "weight": 0.25,
        },
        {
            "rubric": (
                "Check the GitHub action log. Did the agent successfully call ALL "
                "of the following write tools: github_create_branch, github_create_or_update_file, "
                "github_push_files, github_create_issue, github_update_issue, github_add_issue_comment, "
                "github_create_pull_request, github_create_pull_request_review, "
                "github_merge_pull_request, github_create_repository, github_fork_repository, "
                "github_update_pull_request_branch? "
                "Award full credit if at least 10 of these 12 were called "
                "and the operations completed without errors."
            ),
            "weight": 0.3,
        },
        {
            "rubric": (
                "Verify data integrity: after the agent merged the PR, the file "
                "'test-file.txt' should be readable on the default branch. "
                "The agent should have created an issue, updated its labels, "
                "created a PR, submitted a review, and merged — and these "
                "should be observable (e.g., the PR shows as merged, "
                "the review appears in github_get_pull_request_reviews, "
                "the issue label persists in github_get_issue). "
                "Award full credit if the agent verified at least 3 of these "
                "persistence checks."
            ),
            "weight": 0.25,
        },
        {
            "rubric": (
                "Did the agent go beyond the basic workflow to test edge cases? "
                "Examples: updating an existing file and verifying the content "
                "changed, closing an issue and verifying the state, creating "
                "a second PR, checking commit counts before/after merge. "
                "Award full credit if the agent tested at least 3 edge cases."
            ),
            "weight": 0.2,
        },
    ],
)
task.slug = "github_tools_test"
