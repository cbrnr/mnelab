# AGENTS.md

Guidelines for AI coding agents working on this repository.

## Project setup

- This project uses [uv](https://docs.astral.sh/uv/) for package and environment management.
- Install dependencies with `uv sync --all-groups --all-extras`.
- Run the app with `uv run mnelab`.
- Run tests with `uv run pytest`.

## Code style

- Formatting is enforced by [Ruff](https://docs.astral.sh/ruff/). Run both of the following before committing:
  ```
  ruff check --select I --fix
  ruff format
  ```
- Line length is 88 characters (the default). This limit applies to all code, including docstrings.
- Docstrings follow [NumPy style](https://numpydoc.readthedocs.io/en/latest/format.html), but use standard Markdown syntax instead of reStructuredText. In particular, inline code uses single backticks (`` `x` ``), not double backticks (` ``x`` `).
- Inline comments should start with a lower-case letter and be a single sentence where possible.

## Changelog

Every PR must include an entry in the `[UNRELEASED]` section of [CHANGELOG.md](CHANGELOG.md). Add it under the appropriate subsection (`### ✨ Added`, `### 🔧 Fixed`, `### 🌀 Changed`, or `### 🗑️ Removed`). Follow the existing style: a single sentence starting with a capital letter, followed by the PR link and author in parentheses, e.g.:

```
- Add support for XYZ ([#123](https://github.com/cbrnr/mnelab/pull/123) by [Your Name](https://github.com/yourname))
```

## Commit messages

- Use the imperative mood and start with a capital letter (e.g., `Fix crash when loading XDF files`).
- Keep the subject line concise (72 characters or fewer).
