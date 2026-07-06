# CLAUDE.md

Guidelines for AI coding agents working on this repository.

## Project setup

- This project uses [uv](https://docs.astral.sh/uv/) for package and environment management.
- Install dependencies with `uv sync --all-groups --all-extras`.
- Run the app with `uv run mnelab`.
- Run tests with `uv run pytest -W error tests` (CI promotes warnings to errors; a plain `uv run pytest` will miss these).

## Code style

- Formatting is enforced by [Ruff](https://docs.astral.sh/ruff/). Run both of the following before committing:
  ```
  uv run ruff check --fix
  uv run ruff format
  ```
- Line length is 88 characters (the default). This limit applies to all code, including docstrings.
- Docstrings follow [NumPy style](https://numpydoc.readthedocs.io/en/latest/format.html), but use standard Markdown syntax instead of reStructuredText and a line length of 88 characters. In particular, inline code formatting uses single backticks (`` `x` ``), not double backticks (` ``x`` `).
- Inline comments should start with a lower-case letter and be a single sentence where possible.
- Because [PySide6](https://doc.qt.io/qtforpython-6/index.html) is based on the C++-based Qt library, most of its names use camelCase. In your own code, use snake_case wherever possible.
- Every file in `src/` and `tests/` must start with this exact license header, checked by CI (`.github/check_license_headers.py`):
  ```
  # © MNELAB developers
  #
  # License: BSD (3-clause)
  ```

## Changelog

Every PR must include an entry in the `[UNRELEASED]` section of [CHANGELOG.md](CHANGELOG.md). Add it under the appropriate subsection (`### ✨ Added`, `### 🔧 Fixed`, `### 🌀 Changed`, or `### 🗑️ Removed`). Follow the existing style: a single sentence starting with a capital letter, followed by the PR link and author in parentheses, e.g.:

```
- Add support for XYZ ([#123](https://github.com/cbrnr/mnelab/pull/123) by [Your Name](https://github.com/yourname))
```

## Commit messages

- Use the imperative mood and start with a capital letter (e.g., `Fix crash when loading XDF files`).
- Keep the subject line concise (72 characters or fewer).

## Icons

- MNELAB bundles its icons in `src/mnelab/icons`, which contains `light` and `dark` subfolders for the two themes.
- Any added or modified icon must be updated for both themes.
- All icons are SVGs from the [Material Symbols](https://fonts.google.com/icons?utm_source=chatgpt.com) icon set or follow its style.
- To add a new icon:

  1. Download the icon from the Material Symbols website.
  2. Rename it to reflect its intended action.
  3. Place it in `icons/light/actions`.
  4. Edit the SVG and add `fill="black"` to the `<svg>` tag.
  5. Copy the SVG to `icons/dark/actions` and change the fill attribute to `fill="white"`.

## Release

1. Run `uv run tools/release.py prepare X.Y.Z` (with the version to be released). This removes the `.dev0` suffix from the `version` field in `pyproject.toml`, updates the `## [UNRELEASED]` heading in `CHANGELOG.md` with the version and today's date, updates the standalone installer URLs in `README.md` and `docs/quickstart/index.md`, and runs `uv lock`.
2. Review the resulting changes, then commit and push them.
3. Tag the release commit with the version prepended with a `v` (e.g. `v1.7.0`) and push the tag, e.g. `git tag v1.7.0 && git push origin v1.7.0`.
4. A GitHub Action takes care of running the tests, building and uploading wheels to PyPI, building standalone installers, and creating the GitHub release.

This concludes the new release. Now prepare the source for the next planned release as follows:

1. Run `uv run tools/release.py bump X.Y.Z` (with the next planned version). This sets the `version` field to `X.Y.Z.dev0`, starts a fresh `## [UNRELEASED] · YYYY-MM-DD` section at the top of `CHANGELOG.md`, and runs `uv lock`.
2. Commit ("Prepare next dev version") and push.
