# © MNELAB developers
#
# License: BSD (3-clause)

import math

import numpy as np
import pytest
from edfio import Edf, EdfSignal

from mnelab import Model


@pytest.fixture(scope="module")
def edf_files(tmp_path_factory):
    """Generate .edf files for testing purposes."""
    fs = 256
    signals = [
        np.linspace(-1, 1, 30 * fs),
        np.linspace(-10, -15, 30 * fs),
        np.linspace(10, 15, 30 * fs),
    ]
    paths = []
    for i, signal_data in enumerate(signals):
        path = tmp_path_factory.mktemp("data") / f"sample_{i}.edf"
        Edf([EdfSignal(signal_data, sampling_frequency=fs, label="EEG")]).write(path)
        paths.append(path)
    return paths


@pytest.mark.parametrize("duplicate_data", [True, False])
def test_append_data(edf_files, duplicate_data):
    """Test append_data method."""

    model = Model()
    for file in edf_files:
        model.load(file)

    data = [d["data"].get_data()[0] for d in model.data]

    assert len(model.data) == len(edf_files), (
        "Number of data sets in model is not equal to number of files after loading"
    )

    idx_list = [1, 2]  # data sets to append
    model.index = 0  # set current data set
    if duplicate_data:  # adjust for index change if duplicated
        model.duplicate_data()
        idx_list = [idx + 1 if idx >= model.index else idx for idx in idx_list]

    model.append_data(idx_list)

    assert (
        len(model.data) == len(edf_files) + 1 if duplicate_data else len(edf_files)
    ), "Number of data sets in model is not equal to number of files after appending"

    assert model.current["name"].endswith("(appended)"), (
        "Name of appended data set does not match expected name"
    )

    assert len(model.current["data"].times) == sum(len(d) for d in data), (
        "Length of appended data set does not match expected length"
    )

    appended_data = model.current["data"].get_data()[0]

    assert math.isclose(appended_data[0], data[0][0], rel_tol=1e-12), (
        "Value at index 0 is incorrect"
    )

    assert math.isclose(
        appended_data[(idx := len(data[0]) - 1)], data[0][-1], rel_tol=1e-12
    ), f"Value at index {idx} is incorrect"

    assert math.isclose(
        appended_data[(idx := len(data[0]))], data[1][0], rel_tol=1e-12
    ), f"Value at index {idx} is incorrect"

    assert math.isclose(
        appended_data[(idx := len(data[0]) + len(data[1]) - 1)],
        data[1][-1],
        rel_tol=1e-12,
    ), f"Value at index {idx} is incorrect"

    assert math.isclose(
        appended_data[(idx := len(data[0]) + len(data[1]))], data[2][0], rel_tol=1e-12
    ), f"Value at index {idx} is incorrect"

    assert math.isclose(appended_data[-1], data[2][-1], rel_tol=1e-12), (
        "Value at last index is incorrect"
    )
