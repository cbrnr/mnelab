# © MNELAB developers
#
# License: BSD (3-clause)

import numpy as np
import pytest
from edfio import Edf, EdfSignal

from mnelab import MainWindow, Model


# Fixture to generate sample .edf files
@pytest.fixture(scope="module")
def generate_edf_files(tmp_path_factory):
    """
    Use edfio package to generate three temporary .edf files with
    sample EEG data for testing purposes.
    """

    file_path_1 = tmp_path_factory.mktemp("data") / "sample_0.edf"
    signal_1 = [
        EdfSignal(
            np.linspace(-1, 1, 30 * 256),  # Linear signal
            sampling_frequency=256,
            label="sample_EEG_sig",
        ),
    ]
    edf_1 = Edf(signal_1)
    edf_1.write(str(file_path_1))

    # Generate the second .edf file with a sine wave
    file_path_2 = tmp_path_factory.mktemp("data") / "sample_1.edf"
    signal_2 = [
        EdfSignal(
            np.sin(np.linspace(0, 4 * np.pi, 30 * 256)),  # Sine wave
            sampling_frequency=256,
            label="sample_EEG_sig",
        ),
    ]
    edf_2 = Edf(signal_2)
    edf_2.write(str(file_path_2))

    # Generate the third .edf file with a cosine wave
    file_path_3 = tmp_path_factory.mktemp("data") / "sample_2.edf"
    signal_3 = [
        EdfSignal(
            np.cos(np.linspace(0, 4 * np.pi, 30 * 256)),  # Cosine wave
            sampling_frequency=256,
            label="sample_EEG_sig",
        ),
    ]
    edf_3 = Edf(signal_3)
    edf_3.write(str(file_path_3))

    file_paths = [file_path_1, file_path_2, file_path_3]
    return file_paths


# helper functions
def calculate_expected_length(model, names_to_append):
    expected_length = len(model.current["data"].times)
    for d in model.data:
        if d["name"] in names_to_append:
            expected_length += len(d["data"].times)
    return expected_length


def test_append_data(generate_edf_files):
    """
    Test append_data model function with generated temporary .edf files for
    duplicate and overwrite use cases.
    """

    model = Model()
    view = MainWindow(model)
    model.view = view

    count_files = 0
    for file_path in generate_edf_files:
        model.load(file_path)
        count_files += 1

    assert (
        len(model.data) == count_files
    ), "Number of data in model mismatches number of files after loading"

    # Use case 1: Duplicate before appending:
    model.index = 0
    model.duplicate_data()
    names_to_append = ["sample_1", "sample_2"]
    expected_len_after_appending = calculate_expected_length(model, names_to_append)
    model.append_data(names_to_append)

    assert (
        len(model.data) == count_files + 1
    ), "Use-Case #1: Number of data in model mismatches number of files after appending"

    assert (
        "(appended)" in model.current["name"]
    ), "Use-Case #1: Name of appended dataset not changed."

    assert (
        len(model.current["data"].times) == expected_len_after_appending
    ), "Use-Case #1: Expected length mismatch after appending."

    appended_data = model.current["data"].get_data()[0]
    assert appended_data[0] == -1.0, "Value at index 0 is incorrect"
    assert appended_data[5000] == 0.3022659647516594, "Value at index 5000 is incorrect"
    assert (
        appended_data[10000] == -0.6091554131380178
    ), "Value at index 1000 is incorrect"
    assert (
        appended_data[15000] == -0.5542839703974975
    ), "Value at index 15000 is incorrect"
    assert appended_data[-1] == 1.0, "Value at the last index is incorrect"

    # Use case 2: Overwrite:
    model.index = 1
    names_to_append = ["sample_1", "sample_2"]
    expected_len_after_appending = calculate_expected_length(model, names_to_append)
    model.append_data(names_to_append)

    assert (
        len(model.data) == count_files + 1
    ), "Use-Case #2: Number of data in model mismatches number of files after appending"

    assert (
        "(appended)" in model.current["name"]
    ), "Use-Case #2: Name of appended dataset not changed."

    assert (
        len(model.current["data"].times) == expected_len_after_appending
    ), "Use-Case #2: Expected length mismatch after appending."

    appended_data = model.current["data"].get_data()[0]
    assert appended_data[0] == -1.0, "Value at index 0 is incorrect"
    assert (
        appended_data[10000] == -0.6091554131380178
    ), "Value at index 10000 is incorrect"
    assert (
        appended_data[20000] == 0.25786221103227286
    ), "Value at index 20000 is incorrect"
    assert (
        appended_data[30000] == -0.9233081559472038
    ), "Value at index 30000 is incorrect"
    assert appended_data[-1] == 1.0, "Value at the last index is incorrect"
