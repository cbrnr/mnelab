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
    """Generate three .edf files for testing purposes."""
    signals = [
        np.linspace(-1, 1, 30 * 256),
        np.sin(np.linspace(0, 4 * np.pi, 30 * 256)),
        np.cos(np.linspace(0, 4 * np.pi, 30 * 256)),
    ]
    paths = []
    for i, signal_data in enumerate(signals):
        path = tmp_path_factory.mktemp("data") / f"sample_{i}.edf"
        Edf([EdfSignal(signal_data, sampling_frequency=256, label="EEG")]).write(path)
        paths.append(path)

    return paths


# helper functions
def calculate_expected_length(model, names_to_append):
    expected_length = len(model.current["data"].times)
    for d in model.data:
        if d["name"] in names_to_append:
            expected_length += len(d["data"].times)
    return expected_length


def test_append_data(edf_files):
    """Test append_data method."""

    model = Model()

    for file in edf_files:
        model.load(file)

    sample_data_0 = model.data[0]["data"].get_data()[0]
    sample_data_1 = model.data[1]["data"].get_data()[0]
    sample_data_2 = model.data[2]["data"].get_data()[0]
    len_sample_data_0 = len(sample_data_0)
    len_sample_data_1 = len(sample_data_1)
    len_sample_data_2 = len(sample_data_2)

    n_files = len(edf_files)

    assert (
        len(model.data) == n_files
    ), "Number of data sets in model is not equal to number of files after loading"

    # use case 1: duplicate before appending
    model.index = 0
    model.duplicate_data()
    names_to_append = ["sample_1", "sample_2"]
    expected_len = calculate_expected_length(model, names_to_append)
    model.append_data(names_to_append)

    assert (
        len(model.data) == n_files + 1
    ), "Number of data sets in model is not equal to number of files after appending"

    assert model.current["name"].endswith(
        "(appended)"
    ), "Name of appended data set does not match expected name"

    assert (
        len(model.current["data"].times) == expected_len
    ), "Length of appended data set does not match expected length"

    appended_data = model.current["data"].get_data()[0]

    assert math.isclose(
        appended_data[0], sample_data_0[0], rel_tol=1e-12
    ), "Value at index 0 is incorrect"

    assert math.isclose(
        appended_data[len_sample_data_0 - 1],
        sample_data_0[len_sample_data_0 - 1],
        rel_tol=1e-12,
    ), f"Value at index {len_sample_data_0 - 1} is incorrect"

    assert math.isclose(
        appended_data[len_sample_data_0],
        sample_data_1[0],
        rel_tol=1e-12,
    ), f"Value at index {len_sample_data_0} is incorrect"

    assert math.isclose(
        appended_data[len_sample_data_0 + len_sample_data_1 - 1],
        sample_data_1[len_sample_data_1 - 1],
        rel_tol=1e-12,
    ), f"Value at index {len_sample_data_0 + len_sample_data_1 - 1} is incorrect"

    assert math.isclose(
        appended_data[len_sample_data_0 + len_sample_data_1],
        sample_data_2[0],
        rel_tol=1e-12,
    ), f"Value at index {len_sample_data_0 + len_sample_data_1} is incorrect"

    assert math.isclose(
        appended_data[-1],
        sample_data_2[len_sample_data_2 - 1],
        rel_tol=1e-12,
    ), "Value at last index is incorrect"

    # use case 2: Overwrite:
    model.index = 1
    names_to_append = ["sample_1", "sample_2"]
    expected_len = calculate_expected_length(model, names_to_append)
    model.append_data(names_to_append)

    assert (
        len(model.data) == n_files + 1
    ), "Use-Case #2: Number of data in model mismatches number of files after appending"

    assert (
        "(appended)" in model.current["name"]
    ), "Use-Case #2: Name of appended dataset not changed."

    assert (
        len(model.current["data"].times) == expected_len
    ), "Use-Case #2: Expected length mismatch after appending."

    appended_data = model.current["data"].get_data()[0]
    assert math.isclose(
        appended_data[0], sample_data_0[0], rel_tol=1e-12
    ), "Value at index 0 is incorrect"

    assert math.isclose(
        appended_data[len_sample_data_0 - 1],
        sample_data_0[len_sample_data_0 - 1],
        rel_tol=1e-12,
    ), f"Value at index {len_sample_data_0 - 1} is incorrect"

    assert math.isclose(
        appended_data[len_sample_data_0],
        sample_data_1[0],
        rel_tol=1e-12,
    ), f"Value at index {len_sample_data_0} is incorrect"

    assert math.isclose(
        appended_data[len_sample_data_0 + len_sample_data_1 - 1],
        sample_data_1[len_sample_data_1 - 1],
        rel_tol=1e-12,
    ), f"Value at index {len_sample_data_0 + len_sample_data_1 - 1} is incorrect"

    assert math.isclose(
        appended_data[len_sample_data_0 + len_sample_data_1],
        sample_data_2[0],
        rel_tol=1e-12,
    ), f"Value at index {len_sample_data_0 + len_sample_data_1} is incorrect"

    assert math.isclose(
        appended_data[-1],
        sample_data_2[len_sample_data_2 - 1],
        rel_tol=1e-12,
    ), "Value at last index is incorrect"
