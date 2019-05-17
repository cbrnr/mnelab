from importlib import import_module


# contains information whether a specific package is available or not
have = {d: False for d in ["numpy", "scipy", "mne", "matplotlib", "pyxdf",
                           "pyedflib", "picard", "sklearn", "PyQt5"]}

for key, value in have.items():
    try:
        import_module(key)
    except ModuleNotFoundError:
        pass
    else:
        have[key] = True
