# Contributing to UK Housing Ombudsman Disputes Dataset Scraper

We welcome contributions from housing officers, policy analysts, tenant advocates, and software developers at all technical levels.

## Everyone Can Contribute

You don't need to write code to make a valuable contribution.

### Ways to Help (No Coding Required)
- **Report bugs**: Spotted a landlord matching error or a regex issue in the scraper? [File an issue](https://github.com/guyclarkemarshall/HousingOmbudsmanData/issues).
- **Suggest features**: What additional regulatory metrics should we extract?
- **Review for accuracy**: Help verify that compiled categories map cleanly to actual housing dispute contexts.
- **Improve documentation**: Fix typos, add context, or clarify setup steps.
- **Glossary updates**: Help define housing domain terminology in [GLOSSARY.md](docs/GLOSSARY.md).

### Your First Code Contribution
1. Find a issue labelled `good-first-issue`.
2. Comment to claim it.
3. Follow the [Getting Started Guide](docs/guides/getting-started.md).
4. Implement your changes on a feature branch, write unit tests, and open a Pull Request.

---

## Contributor Ladder

- **Level 1: Reporter**: Files clear issues, reports bugs, reviews docs for domain accuracy.
- **Level 2: Documenter**: Improves guides, glossary, and updates housing contextual information.
- **Level 3: First-Time Coder**: Solves small issues with mentorship, makes first PR, adds test cases.
- **Level 4: Regular Contributor**: Updates compilation scripts, maintains validation schemas, reviews PRs.
- **Level 5: Maintainer**: Exercises merge authority, guides strategic roadmaps.

---

## Technical Workflow for Developers

### Branching Strategy
Name branches prefixing the work type:
- `feature/` - New scraper capabilities or database metrics
- `fix/` - Bug fixes (e.g. regex updates)
- `docs/` - Documentation changes
- `test/` - Add/improve tests
- `refactor/` - Refactoring code

### Commit Messages
We follow Conventional Commits format:
- `feat(insights): extract Awaab's Law citation counts`
- `fix(landlords): standardize Peabody Trust naming`
- `docs(glossary): add void property definitions`
- `test(heuristic): assert compensation amount correctness`

### Setup and Verification
1. Install `uv` (a fast Python package manager).
2. Run `scripts/setup.ps1` (Windows) or `scripts/setup.sh` (Unix) to bootstrap the environment and extract datasets.
3. Run tests using `uv run python -m pytest`.
4. Ensure code formatting is clean before proposing changes.
