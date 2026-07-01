# AGENTS.md

Guidelines for AI coding agents working on this repository.

## Project setup

- This project uses [uv](https://docs.astral.sh/uv/) for package and environment management.
- Install dependencies with `uv sync --all-groups --all-extras`.
- Run the app with `uv run mnelab`.
- Run tests with `uv run pytest -W error tests` (CI promotes warnings to errors; a plain `uv run pytest` will miss these).

## Code style

- Formatting is enforced by [Ruff](https://docs.astral.sh/ruff/). Run both of the following before committing:
  ```
  uv run ruff check --select I --fix
  uv run ruff format
  ```
  CI also runs `ruff check` (full lint, not just import sorting) and `ruff format --diff`, so also run `uv run ruff check` before committing.
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

1. Remove the `.dev0` suffix from the `version` field in `pyproject.toml` (and/or adapt the version to be released if necessary).
2. Run `uv lock` to update `uv.lock` with the new version.
3. Update the section in `CHANGELOG.md` corresponding to the new release with the version and current date.
4. Update the section on the standalone installers in `README.md` and `docs/tutorial/index.md` (use the to-be-released version in the URLs, e.g., https://github.com/cbrnr/mnelab/releases/download/v1.0.3/MNELAB-1.0.3.exe).
5. Commit these changes and push.
6. Create a new release on GitHub and use the version as the tag name (make sure to prepend the version with a `v`, e.g. `v0.7.0`).
7. A GitHub Action takes care of building and uploading wheels to PyPI as well as adding standalone installers to the release.

This concludes the new release. Now prepare the source for the next planned release as follows:

1. Update the `version` field to the next planned release and append `.dev0`.
2. Run `uv lock` to update `uv.lock` with the new version.
3. Start a new section at the top of `CHANGELOG.md` titled `## [UNRELEASED] · YYYY-MM-DD`.
4. Commit ("Prepare next dev version") and push.
