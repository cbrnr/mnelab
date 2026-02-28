# MNELAB Flatpak

Files in this directory produce a Flatpak bundle of MNELAB for Linux, conforming to [Flathub](https://flathub.org) submission requirements.

## Directory contents

| File | Purpose |
|---|---|
| `io.github.cbrnr.mnelab.yml` | Flatpak manifest (main build recipe) |
| `io.github.cbrnr.mnelab.desktop` | XDG desktop entry (application launcher) |
| `io.github.cbrnr.mnelab.metainfo.xml` | AppStream metadata (required by Flathub) |
| `python3-pyside6.json` | Pre-fetched PySide6 wheel sources (generated – see below) |
| `python3-mnelab-deps.json` | Pre-fetched wheel sources for all other deps (generated – see below) |
| `generate-pip-sources.sh` | Script to regenerate both JSON files |

---

## Per-release checklist

### 0 · One-time setup

Install the Flatpak build tools and runtime (required for both generating pip sources and building the Flatpak):

```bash
flatpak install flathub org.freedesktop.Platform//24.08 org.freedesktop.Sdk//24.08
```

### 1 · Tag the release

```bash
git tag v1.4.0
git push origin v1.4.0
```

### 2 · Update the manifest

In `io.github.cbrnr.mnelab.yml`, under the `mnelab` module's `git` source:

```yaml
tag: v1.4.0
commit: <exact SHA of the tagged commit>  # git rev-parse v1.4.0^{}
```

### 3 · Regenerate the pip sources

Flathub builds have no network access, so every wheel must be declared explicitly.
PySide6 is handled separately from the other deps because `flatpak-pip-generator`
constructs wrong PyPI API URLs for its sub-packages (`pyside6_essentials`,
`pyside6_addons`, `shiboken6`) — the tool uses underscores but the PyPI JSON API
expects hyphens.

```bash
./generate-pip-sources.sh  # updates python3-pyside6.json and python3-mnelab-deps.json
```

Commit both updated JSON files.

### 4 · Add a `<release>` entry to the metainfo file

In `io.github.cbrnr.mnelab.metainfo.xml`, add:

```xml
<release version="1.4.0" date="YYYY-MM-DD">
  <url type="details">https://github.com/cbrnr/mnelab/blob/main/CHANGELOG.md</url>
  <description><p>…brief summary…</p></description>
</release>
```

### 5 · Validate locally

First, make sure you have completed the previous steps:
- Step 0: The Flatpak SDK is installed (one-time)
- Step 3: `python3-pyside6.json` and `python3-mnelab-deps.json` have been generated and are present in this directory
- Step 4: Only needed if you want `appstreamcli validate` to pass — for just building and running the app locally it can be skipped

Build and install into your local user Flatpak repo:

```bash
flatpak-builder --force-clean --install --user builddir io.github.cbrnr.mnelab.yml
```

Run it:

```bash
flatpak run io.github.cbrnr.mnelab
```

Validate the metadata files:

```bash
appstreamcli validate io.github.cbrnr.mnelab.metainfo.xml
desktop-file-validate io.github.cbrnr.mnelab.desktop
```

Clean up when done:

```bash
flatpak uninstall io.github.cbrnr.mnelab
flatpak uninstall --unused
rm -rf builddir .flatpak-builder
```

---

## Steps to submit to Flathub

1. **Fork the Flathub repository**
   [https://github.com/flathub/flathub](https://github.com/flathub/flathub)

2. **Open a New App request**
   File an issue at [https://github.com/flathub/flathub/issues/new?template=new_app.yml](https://github.com/flathub/flathub/issues/new?template=new_app.yml).
   The Flathub team will create a dedicated app repository
   `https://github.com/flathub/io.github.cbrnr.mnelab` and grant you push access.

3. **Push the manifest files to the new repo**
   The repository must contain, at minimum:
   - `io.github.cbrnr.mnelab.yml`
   - `io.github.cbrnr.mnelab.metainfo.xml`  ← may be committed inside the
     app source tree instead
   - `io.github.cbrnr.mnelab.desktop` ← same
   - `python3-pyside6.json`
   - `python3-mnelab-deps.json`

4. **Open a Pull Request to `flathub/io.github.cbrnr.mnelab`**
   The automated Flathub CI (buildbot) will build and test the manifest.
   Fix any reported errors.

5. **Review and merge**
   A Flathub reviewer approves the PR.  Once merged, the app appears on
   [https://flathub.org](https://flathub.org) within hours.

6. **Updates**
   For each new MNELAB release, repeat steps 1–5 from the per-release
   checklist above and open a PR against the `flathub/io.github.cbrnr.mnelab`
   repository.

---

## Useful references

- Flathub submission guidelines: <https://docs.flathub.org/docs/for-app-authors/submission>
- AppStream metainfo spec: <https://www.freedesktop.org/software/appstream/docs/>
- flatpak-pip-generator: <https://github.com/flatpak/flatpak-builder-tools/tree/master/pip>
- Flathub manifest requirements: <https://docs.flathub.org/docs/for-app-authors/requirements>
