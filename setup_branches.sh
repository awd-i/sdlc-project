#!/usr/bin/env bash
# setup_branches.sh
#
# Prepares a wireguard-go clone with the three branches required by the
# SDLC template task:
#
#   ratelimiter_bug_baseline  -- contains the seeded off-by-one bug
#   ratelimiter_bug_test      -- adds hidden grading test file
#   ratelimiter_bug_golden    -- the correct fix
#
# Usage:
#   git clone https://github.com/<your-fork>/wireguard-go.git
#   cd wireguard-go
#   bash ../setup_branches.sh
#
# After running, push all branches:
#   git push origin ratelimiter_bug_baseline ratelimiter_bug_test ratelimiter_bug_golden

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Create baseline branch (with the bug)
git checkout -b ratelimiter_bug_baseline master

# Seed the bug: set initial tokens to maxTokens instead of maxTokens - packetCost
sed -i.bak 's/entry\.tokens = maxTokens - packetCost/entry.tokens = maxTokens/' ratelimiter/ratelimiter.go && rm ratelimiter/ratelimiter.go.bak

git add ratelimiter/ratelimiter.go
git commit -m "baseline: seed ratelimiter initial-burst off-by-one bug"

echo "Created ratelimiter_bug_baseline"

# 2. Create test branch (baseline + hidden test file)
git checkout -b ratelimiter_bug_test ratelimiter_bug_baseline

cp "${SCRIPT_DIR}/ratelimiter_burst_test.go" ratelimiter/ratelimiter_burst_test.go

git add ratelimiter/ratelimiter_burst_test.go
git commit -m "test: add burst-count regression tests for ratelimiter"

echo "Created ratelimiter_bug_test"

# 3. Create golden branch (baseline + the fix, line-specific to avoid touching line 126)
git checkout -b ratelimiter_bug_golden ratelimiter_bug_baseline

# Replace only the first occurrence (line 109), not the one at line 126
perl -i -pe 'if (!$n && /entry\.tokens = maxTokens/) { s/entry\.tokens = maxTokens/entry.tokens = maxTokens - packetCost/; $n=1 }' ratelimiter/ratelimiter.go

git add ratelimiter/ratelimiter.go
git commit -m "fix: correct initial token count in ratelimiter"

echo "Created ratelimiter_bug_golden"

git checkout ratelimiter_bug_baseline

echo ""
echo "All branches created. Push them with:"
echo "  git push origin ratelimiter_bug_baseline ratelimiter_bug_test ratelimiter_bug_golden"
