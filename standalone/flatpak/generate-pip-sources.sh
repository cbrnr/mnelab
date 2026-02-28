#!/usr/bin/env bash
# generate-pip-sources.sh
#
# Produces two JSON files that Flatpak uses to download Python wheels offline:
#
# - python3-pyside6.json:
#       PySide6 and its sub-packages must be handled separately, because
#       flatpak-pip-generator constructs wrong PyPI API URLs for packages whose names
#       contain underscores.
# - python3-mnelab-deps.json:
#       All other dependencies.
#
# Run this script once per release and commit both JSON files.
#
# Prerequisites
# -------------
#   uv (https://docs.astral.sh/uv/) — already used by this project
#
# Usage
# -----
#   cd standalone/flatpak
#   ./generate-pip-sources.sh

set -euo pipefail

GENERATOR="uvx --from flatpak-pip-generator flatpak_pip_generator"
RUNTIME="org.freedesktop.Sdk//24.08"

# ── PySide6 (separate file, custom generator) ────────────────────────────
#
# Pin to the exact version pip resolves inside the SDK sandbox. To find the current
# version, run:
#   flatpak run --command=pip3 --devel org.freedesktop.Sdk//24.08 show pyside6 2>/dev/null | grep Version
# Then update PYSIDE6_VERSION below accordingly.
PYSIDE6_VERSION="6.10.2"
echo "Generating python3-pyside6.json for pyside6==${PYSIDE6_VERSION} ..."

python3 - "${PYSIDE6_VERSION}" <<'EOF'
import json
import sys
import urllib.request

version = sys.argv[1]

# PySide6 is split into sub-packages; all must be pinned to the same version
# shiboken6 uses its own versioning (same version number as PySide6 releases)
PACKAGES = ["shiboken6", "pyside6-essentials", "pyside6-addons", "pyside6"]

# Flatpak Linux arch names, mapped from wheel platform tags
ARCH_MAP = {
    "x86_64": "x86_64",
    "aarch64": "aarch64",
}

sources = []
install_args = []

for pkg in PACKAGES:
    url = f"https://pypi.org/pypi/{pkg}/{version}/json"
    with urllib.request.urlopen(url) as r:
        data = json.loads(r.read())

    install_args.append(f"{pkg}=={version}")
    urls = data["urls"]

    for entry in urls:
        filename = entry["filename"]
        # Keep only manylinux wheels (Linux Flatpak targets)
        if "manylinux" not in filename and "linux" not in filename:
            continue
        sha256 = entry["digests"]["sha256"]
        dl_url = entry["url"]

        # Determine architecture from the wheel filename
        arch = None
        for tag, flatpak_arch in ARCH_MAP.items():
            if tag in filename:
                arch = flatpak_arch
                break

        source = {"type": "file", "url": dl_url, "sha256": sha256}
        if arch:
            source["only-arches"] = [arch]
        sources.append(source)

module = {
    "name": "python3-pyside6",
    "buildsystem": "simple",
    "build-commands": [
        "pip3 install --no-index --find-links=. --prefix=/app " + " ".join(install_args)
    ],
    "sources": sources,
}

with open("python3-pyside6.json", "w") as f:
    json.dump(module, f, indent=4)
    f.write("\n")

print(f"  written python3-pyside6.json ({len(sources)} wheel(s))")
EOF

# ── All other dependencies ────────────────────────────────────────────────
PACKAGES=(
    # build backend (required by mnelab's pyproject.toml)
    "uv-build>=0.10.6,<0.11.0"
    "black>=25.11.0"
    "edfio>=0.4.10"
    "isort>=7.0.0"
    "matplotlib>=3.8.0"
    "mne>=1.10.2"
    "numpy>=2.0.0"
    "onnx>=1.20.0"
    "pybv>=0.7.4"
    "pybvrf>=0.1.0"
    "pyxdf>=1.16.4"
    "scipy>=1.14.1"
    # optional
    "autoreject>=0.4.0"
    "mne-qt-browser>=0.6.2"
    "python-picard>=0.8.0"
    "scikit-learn>=1.3.0"
)

echo "Generating python3-mnelab-deps.json ..."
# flatpak-pip-generator writes the file before crashing with an ImportError
# (bug in the tool). Temporarily disable errexit so the script continues,
# then verify the file was actually written.
# Stderr is filtered to suppress the known post-save ImportError traceback
# while still showing any genuine errors.
set +e
${GENERATOR} \
    --runtime "${RUNTIME}" \
    --output python3-mnelab-deps \
    "${PACKAGES[@]}" 2>&1 \
    | grep -v "ImportError\|cannot import name\|flatpak_pip_generator\|Traceback\|File \"/home" \
    | grep -v "^$" >&2 || true
GENERATOR_EXIT=${PIPESTATUS[0]}
set -e
if [ ! -f python3-mnelab-deps.json ]; then
    echo "ERROR: python3-mnelab-deps.json was not created (generator exited $GENERATOR_EXIT)"
    exit 1
fi

# ── Post-process: enforce wheels-only install ─────────────────────────────
# flatpak-pip-generator sometimes includes sdists in the sources. Installing
# an sdist in the Flatpak sandbox fails because build backends (hatchling,
# flit, etc.) are not available. Patch both JSON files to add
# --only-binary :all: so pip errors rather than silently falling back to
# building from source.
echo "Patching JSON files to enforce wheel-only installs ..."
python3 - <<'PYEOF'
import json, pathlib, re, urllib.request

PYTHON_VERSION = (3, 12)   # matches org.freedesktop.Sdk//24.08
ARCH_TAGS = {
    "x86_64":  ["x86_64"],
    "aarch64": ["aarch64"],
}

def pypi_url(name, version):
    # PyPI JSON API requires hyphens, not underscores
    name = re.sub(r"[-_.]+", "-", name).lower()
    return f"https://pypi.org/pypi/{name}/{version}/json"

def wheel_compatible(filename):
    """Return True if the wheel is installable on Python 3.12 Linux x86_64 or aarch64."""
    if not filename.endswith(".whl"):
        return False
    parts = filename[:-4].split("-")
    if len(parts) < 5:
        return False
    py_tag, abi_tag, plat_tag = parts[-3], parts[-2], parts[-1]

    # Pure-Python wheels (none-any) are always compatible
    if abi_tag == "none" and plat_tag == "any":
        return any(
            t in ("py3", "py2.py3", "py2") or t.startswith("cp3") or t.startswith("pp3")
            for t in py_tag.split(".")
        )

    # Platform wheels must target Linux x86_64 or aarch64
    if "linux" not in plat_tag:
        return False
    if not any(a in plat_tag for a in ("x86_64", "aarch64")):
        return False

    # abi=none, platform-specific (e.g. Rust/Go binaries like uv-build, ruff):
    # py3-none-manylinux_* — compatible if py_tag is py3
    if abi_tag == "none":
        return any(t in ("py3", "py2.py3") or t.startswith("cp3") for t in py_tag.split("."))

    # abi3 (stable ABI) wheels are forward-compatible: cpXYZ-abi3 works on
    # Python >= X.Y.Z, so accept if version <= 3.12
    if abi_tag == "abi3":
        for tag in py_tag.split("."):
            if tag.startswith("cp"):
                try:
                    if int(tag[2:]) <= PYTHON_VERSION[0] * 100 + PYTHON_VERSION[1]:
                        return True
                except ValueError:
                    pass
        return False

    # cpXYZ-cpXYZ wheels are version-specific: only accept exact 3.12
    target = f"cp{PYTHON_VERSION[0]}{PYTHON_VERSION[1]}"
    return any(t == target for t in py_tag.split("."))

def arch_for_wheel(filename):
    plat = filename[:-4].split("-")[-1]
    for arch in ("aarch64", "x86_64"):
        if arch in plat:
            return arch
    return None  # universal

def replace_sdists(sources):
    new_sources = []
    for src in sources:
        url = src.get("url", "")
        filename = url.split("/")[-1].split("?")[0]
        if not filename.endswith(".tar.gz"):
            new_sources.append(src)
            continue
        # Extract package name and version from sdist filename
        m = re.match(r"^(.+?)-(\d[^-]*)\.tar\.gz$", filename)
        if not m:
            new_sources.append(src)
            continue
        pkg_name, pkg_version = m.group(1), m.group(2)
        api = pypi_url(pkg_name, pkg_version)
        print(f"    replacing sdist {filename} with wheels ...")
        try:
            with urllib.request.urlopen(api) as r:
                data = json.loads(r.read())
        except Exception as e:
            print(f"    WARNING: could not query PyPI for {pkg_name}=={pkg_version}: {e}")
            new_sources.append(src)
            continue
        wheels_added = 0
        seen_arches = set()
        for entry in data["urls"]:
            fn = entry["filename"]
            if not wheel_compatible(fn):
                continue
            arch = arch_for_wheel(fn)
            key = arch or "any"
            if key in seen_arches:
                continue
            seen_arches.add(key)
            wheel_src = {"type": "file", "url": entry["url"], "sha256": entry["digests"]["sha256"]}
            if arch:
                wheel_src["only-arches"] = [arch]
            new_sources.append(wheel_src)
            wheels_added += 1
        if wheels_added == 0:
            print(f"    WARNING: no compatible wheels found for {pkg_name}=={pkg_version}, keeping sdist")
            new_sources.append(src)
    return new_sources

def patch_module(module):
    # Fix build-commands: add --only-binary :all:
    cmds = module.get("build-commands", [])
    module["build-commands"] = [
        cmd.replace("pip3 install", "pip3 install --only-binary :all:", 1)
        if cmd.startswith("pip3 install") and "--only-binary" not in cmd
        else cmd
        for cmd in cmds
    ]
    # Fix sources: replace sdists with wheels
    if "sources" in module:
        module["sources"] = replace_sdists(module["sources"])
    # Recurse
    for sub in module.get("modules", []):
        patch_module(sub)

for path in pathlib.Path(".").glob("python3-*.json"):
    data = json.loads(path.read_text())
    modules = data if isinstance(data, list) else [data]
    for m in modules:
        patch_module(m)
    path.write_text(json.dumps(data, indent=4) + "\n")
    print(f"  patched {path}")
PYEOF

echo "Done. Review both JSON files and commit them."
