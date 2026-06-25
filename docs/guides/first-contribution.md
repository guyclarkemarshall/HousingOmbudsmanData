# First Contribution Guide

Welcome! We are excited to have you contribute. This step-by-step guide walks you through making your very first code contribution.

---

## 1. Pick an Issue
Go to our [issues page](https://github.com/guyclarkemarshall/HousingOmbudsmanData/issues) and look for issues with the label `good-first-issue`. These are small tasks designed for newcomers. 
Comment on the issue to let us know you want to work on it.

## 2. Set Up Your Environment
Follow the instructions in our [Getting Started Guide](getting-started.md) to install dependencies and verify the test suite passes on your machine.

## 3. Create a Feature Branch
Always work on a separate branch, never directly on `main`. Make sure to pull the latest changes first:

```bash
git checkout main
git pull
git checkout -b feature/my-cool-improvement
```

## 4. Make Your Changes
Write your code, following the guidelines in [CLAUDE.md](../../CLAUDE.md) (e.g. use parameterised database queries and preserve data anonymity).

- If you introduce a new housing-specific concept or data metric, update our [GLOSSARY.md](../GLOSSARY.md) and [DATA-STANDARDS.md](../DATA-STANDARDS.md) files.

## 5. Add or Update Tests
Add unit tests for your logic in the relevant file under `tests/` (e.g. `tests/test_extraction_functions.py` if editing regex helpers).

Run the tests to make sure everything passes:
```bash
uv run python -m pytest
```

## 6. Commit Your Work
Commit your changes using Conventional Commits guidelines:

```bash
git add .
git commit -m "feat(insights): add parser for staff training reviews"
```

## 7. Open a Pull Request
Push your branch to GitHub and create a Pull Request:

```bash
git push -u origin feature/my-cool-improvement
```

Fill out the Pull Request Template checklist, submit it as a draft, and tag `@guyclarkemarshall` for feedback. We review all first-time contributor PRs within 48 hours and are happy to pair program to help you get it merged!
