# © MNELAB developers
#
# License: BSD (3-clause)

import importlib
import sys
from importlib import metadata as importlib_metadata
from importlib import util as importlib_util
from pathlib import Path
from types import SimpleNamespace


def _load_dependencies_module(monkeypatch, modules):
    module_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "mnelab"
        / "utils"
        / "dependencies.py"
    )

    def fake_metadata_version(_name):
        raise importlib_metadata.PackageNotFoundError

    def fake_import_module(name):
        if name in modules:
            return modules[name]
        raise ImportError(name)

    monkeypatch.setattr(importlib_metadata, "version", fake_metadata_version)
    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    module_name = "mnelab_test_dependencies"
    sys.modules.pop(module_name, None)
    spec = importlib_util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not create module spec for dependencies.py")
    module = importlib_util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_standalone_fallback_detects_importable_dependencies(monkeypatch):
    modules = {
        "PySide6": SimpleNamespace(__version__="6.9.4"),
        "matplotlib": SimpleNamespace(__version__="3.10.0"),
        "scipy": SimpleNamespace(__version__="1.14.1"),
        "pyxdf": SimpleNamespace(__version__="1.16.0"),
        "pybvrf": SimpleNamespace(__version__="0.1.1"),
        "black": SimpleNamespace(__version__="25.0.0"),
        "onnx": SimpleNamespace(__version__="1.20.0"),
        "picard": SimpleNamespace(__version__="0.8.0"),
    }

    dependencies = _load_dependencies_module(monkeypatch, modules)

    assert dependencies.have["pyside6"] == "6.9.4"
    assert dependencies.have["matplotlib"] == "3.10.0"
    assert dependencies.have["scipy"] == "1.14.1"
    assert dependencies.have["pyxdf"] == "1.16.0"
    assert dependencies.have["pybvrf"] == "0.1.1"
    assert dependencies.have["black"] == "25.0.0"
    assert dependencies.have["onnx"] == "1.20.0"
    assert dependencies.have["python-picard"] == "0.8.0"


def test_standalone_fallback_keeps_false_for_missing_import(monkeypatch):
    dependencies = _load_dependencies_module(monkeypatch, modules={})

    assert dependencies.have["pyside6"] is False
