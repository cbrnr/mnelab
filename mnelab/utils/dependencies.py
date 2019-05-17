from importlib import import_module


# deps contains information whether a specific package is available or not
have = {d: False for d in ["numpy", "scipy", "mne", "matplotlib", "pyxdf",
                           "pyedflib", "picard", "sklearn"]}

for key, value in have.items():
    try:
        import_module(key)
    except ModuleNotFoundError:
        pass
    else:
        have[key] = True
