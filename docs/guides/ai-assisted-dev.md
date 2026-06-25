# AI-Assisted Development Guide

AI tools (like Claude Code or the Gemini Antigravity IDE) are powerful coding accelerators. However, as this project serves the UK social housing sector, AI agents must work within strict constraints to maintain data integrity, security, and accessibility.

---

## Machine-Readable Coding Standard

Our root [CLAUDE.md](../../CLAUDE.md) file acts as the project constitution for AI agents. When you launch an AI coding assistant in this repository, it automatically reads `CLAUDE.md` to understand:
1. **Core Domain Context**: Specifically, our focus on social housing rules and resident data anonymity.
2. **Layer Boundaries**: To prevent files from importing disallowed helper libraries.
3. **Imperative Coding Rules**: For parameterising SQLite database queries and testing.

## Pre-Tool Enforcement Hooks

To protect the codebase from accidental destructive modifications during automated or autonomous development, the project includes hooks in `.claude/hooks/` configured by `.claude/settings.json`.

### 1. Protected Files Hook (`protect-files.sh`)
This hook physically blocks AI agents from modifying the following critical system files:
- AI constitution files (`CLAUDE.md`)
- Project roadmap and governance structures (`MASTERPLAN.md`, `GOVERNANCE.md`, `CODE_OF_CONDUCT.md`)
- Relational schema decisions (`docs/architecture/adr/*`)
- Data and security standards (`docs/SECURITY.md`, `docs/DATA-STANDARDS.md`)
- Repository configurations (`.gitignore`, `.github/*`, CI workflows)

If an agent needs to change one of these files, it must outline the requested changes in a handoff document for human-in-the-loop validation.

### 2. Restricted Commands Hook (`restrict-commands.sh`)
This hook prevents agents from running dangerous terminal commands:
- Force pushing (`git push --force`)
- Hard resetting git trees (`git reset --hard`)
- Bypassing pre-commit checks (`git commit --no-verify`)

---

## Best Practices for Developers using AI

- **Explain the Why**: Ask your AI assistant why a particular text-splitting regex pattern was designed or chosen.
- **Verify Domain Knowledge**: If an AI assistant suggests a category mapping or database field name that runs counter to standard UK housing terms (e.g. suggesting "vacant" instead of the sector standard "void"), trust your domain knowledge and correct the assistant.
- **TDD First**: Ask the AI assistant to write tests under `/tests/` *before* implementing the parsing logic to verify coverage catches all boundary patterns.
