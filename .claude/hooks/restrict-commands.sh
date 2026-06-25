#!/bin/bash
# Blocks dangerous commands. Restricted ops → handoff plan.

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
[[ -z "$COMMAND" ]] && exit 0

STRIPPED=$(echo "$COMMAND" | sed '/<<.*EOF/,/^EOF/d')

# Force push
echo "$STRIPPED" | grep -qE 'git\s+push\s+.*--force|git\s+push\s+.*-f\b' && \
  { echo "Use normal git push only." >&2; exit 2; }

# Hard reset
echo "$STRIPPED" | grep -qE 'git\s+reset\s+--hard' && \
  { echo "Use git stash push -u instead." >&2; exit 2; }

# git clean without dry-run
echo "$STRIPPED" | grep -qE 'git\s+clean\s+.*-[a-zA-Z]*f' && \
  ! echo "$STRIPPED" | grep -qE 'git\s+clean\s+.*-[a-zA-Z]*n' && \
  { echo "Run git clean -n first." >&2; exit 2; }

# Skip hooks
echo "$STRIPPED" | grep -qE 'git\s+.*--no-verify' && \
  { echo "Fix the hook failure instead of skipping." >&2; exit 2; }

# Database migrations
echo "$STRIPPED" | grep -qE 'migrate:up|migrate:down' && \
  { echo "Document migration in handoff plan." >&2; exit 2; }

# Production deployment
echo "$STRIPPED" | grep -qE 'railway\s+up|fly\s+deploy|heroku\s+.*push' && \
  { echo "Document deployment in handoff plan." >&2; exit 2; }

exit 0
