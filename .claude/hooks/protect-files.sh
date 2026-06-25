#!/bin/bash
# Blocks edits to protected files. Changes → handoff plan instead.

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
[[ -z "$FILE_PATH" ]] && exit 0

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
REL_PATH="${FILE_PATH#$PROJECT_DIR/}"

BLOCKED=false
REASON=""

case "$REL_PATH" in
  # Governance & direction
  CLAUDE.md|*/CLAUDE.md)          BLOCKED=true; REASON="Agent constitution file" ;;
  MASTERPLAN.md)                  BLOCKED=true; REASON="Project direction" ;;
  GOVERNANCE.md)                  BLOCKED=true; REASON="Governance document" ;;
  CODE_OF_CONDUCT.md)             BLOCKED=true; REASON="Code of conduct" ;;
  LICENSE)                        BLOCKED=true; REASON="Licence file" ;;

  # Standards
  docs/architecture/adr/*)        BLOCKED=true; REASON="Architecture decision record" ;;
  docs/SECURITY.md)               BLOCKED=true; REASON="Security patterns" ;;
  docs/TESTING.md)                BLOCKED=true; REASON="Testing standards" ;;
  docs/ACCESSIBILITY.md)          BLOCKED=true; REASON="Accessibility standards" ;;
  docs/DATA-STANDARDS.md)         BLOCKED=true; REASON="Data standards" ;;

  # Infrastructure & config
  .gitignore)                     BLOCKED=true; REASON="Git configuration" ;;
  .github/*)                      BLOCKED=true; REASON="CI/CD configuration" ;;
  .env|.env.*|*.env|*.env.*)      BLOCKED=true; REASON="Environment/secrets" ;;
  Dockerfile*|*/Dockerfile*)      BLOCKED=true; REASON="Infrastructure" ;;
  docker-compose*|*/docker-compose*) BLOCKED=true; REASON="Infrastructure" ;;
  **/migrations/*)                BLOCKED=true; REASON="Database migration" ;;
esac

if [[ "$BLOCKED" == "true" ]]; then
  echo "Protected file — document needed changes in a handoff plan instead. ($REASON: $REL_PATH)" >&2
  exit 2
fi
exit 0
