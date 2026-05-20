# © MNELAB developers
#
# License: BSD (3-clause)

import math
from pathlib import Path

import numpy as np
import pytest
from edfio import Edf, EdfSignal
from mne import Annotations

from mnelab.model import InvalidAnnotationsError, Model


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


@pytest.fixture
def model_with_data(tmp_path):
    """Model with a single 30-second EDF file loaded."""
    fs = 256
    signal = np.zeros(30 * fs)
    path = tmp_path / "sample.edf"
    Edf([EdfSignal(signal, sampling_frequency=fs, label="EEG")]).write(path)
    model = Model()
    model.load(path)
    return model


def _write_annotations_csv(path, rows, header=True):
    """Write a CSV annotation file."""
    with open(path, "w") as f:
        if header:
            f.write("type,onset,duration\n")
        for row in rows:
            f.write(",".join(str(v) for v in row) + "\n")


def test_import_annotations_basic(model_with_data, tmp_path):
    """Imported annotations are added to the data."""
    csv = tmp_path / "annots.csv"
    _write_annotations_csv(csv, [("BAD", 1.0, 0.5), ("BAD", 5.0, 1.0)])
    model_with_data.import_annotations(csv)
    annots = model_with_data.current["data"].annotations
    assert len(annots) == 2
    assert list(annots.description) == ["BAD", "BAD"]
    np.testing.assert_allclose(annots.onset, [1.0, 5.0])
    np.testing.assert_allclose(annots.duration, [0.5, 1.0])


def test_import_annotations_merges_with_existing(model_with_data, tmp_path):
    """Imported annotations are appended to already-existing annotations."""
    model_with_data.current["data"].set_annotations(
        Annotations([2.0], [0.25], ["EXISTING"])
    )
    csv = tmp_path / "annots.csv"
    _write_annotations_csv(csv, [("NEW", 10.0, 1.0)])
    model_with_data.import_annotations(csv)
    annots = model_with_data.current["data"].annotations
    assert len(annots) == 2
    assert "EXISTING" in annots.description
    assert "NEW" in annots.description


def test_import_annotations_filter_by_type(model_with_data, tmp_path):
    """Only annotation types listed in `types` are imported."""
    csv = tmp_path / "annots.csv"
    _write_annotations_csv(csv, [("BAD", 1.0, 0.5), ("GOOD", 5.0, 1.0)])
    model_with_data.import_annotations(csv, types=["BAD"])
    annots = model_with_data.current["data"].annotations
    assert len(annots) == 1
    assert annots.description[0] == "BAD"


@pytest.mark.parametrize(
    "rows",
    [
        pytest.param([("BAD", "abc", "xyz")], id="non_numeric_values"),
        pytest.param([("BAD", 9999.0, 1.0)], id="outside_range"),
    ],
)
def test_import_annotations_invalid_input(model_with_data, tmp_path, rows):
    """Invalid CSV content raises InvalidAnnotationsError."""
    csv = tmp_path / "bad.csv"
    _write_annotations_csv(csv, rows)
    with pytest.raises(InvalidAnnotationsError):
        model_with_data.import_annotations(csv)


def test_import_annotations_binary_file(model_with_data, tmp_path):
    """A binary file raises InvalidAnnotationsError."""
    binary = tmp_path / "binary.csv"
    binary.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\xff\xfe")
    with pytest.raises(InvalidAnnotationsError):
        model_with_data.import_annotations(binary)


def test_import_annotations_invalid_header(model_with_data, tmp_path):
    """A file without the expected CSV header raises InvalidAnnotationsError."""
    csv = tmp_path / "bad_header.csv"
    csv.write_text("afsklasdjfkasdikfkasdjklfs\n")
    with pytest.raises(InvalidAnnotationsError):
        model_with_data.import_annotations(csv)


def test_import_annotations_outside_range_does_not_change_existing(
    model_with_data, tmp_path
):
    """When an invalid file is rejected, pre-existing annotations are unchanged."""
    model_with_data.current["data"].set_annotations(
        Annotations([2.0], [0.25], ["EXISTING"])
    )
    csv = tmp_path / "out_of_range.csv"
    _write_annotations_csv(csv, [("BAD", 9999.0, 1.0)])
    with pytest.raises(InvalidAnnotationsError):
        model_with_data.import_annotations(csv)
    annots = model_with_data.current["data"].annotations
    assert len(annots) == 1
    assert annots.description[0] == "EXISTING"


def test_import_annotations_no_type_column(model_with_data, tmp_path):
    """A two-column file (onset,duration) uses the supplied description."""
    csv = tmp_path / "no_type.csv"
    with open(csv, "w") as f:
        f.write("onset,duration\n")
        f.write("1.0,0.5\n")
        f.write("5.0,1.0\n")
    model_with_data.import_annotations(csv, description="BAD")
    annots = model_with_data.current["data"].annotations
    assert len(annots) == 2
    assert list(annots.description) == ["BAD", "BAD"]
    np.testing.assert_allclose(annots.onset, [1.0, 5.0])
    np.testing.assert_allclose(annots.duration, [0.5, 1.0])


def test_import_annotations_no_type_column_default_description(
    model_with_data, tmp_path
):
    """A two-column file without a supplied description defaults to 'annotation'."""
    csv = tmp_path / "no_type.csv"
    with open(csv, "w") as f:
        f.write("onset,duration\n")
        f.write("1.0,0.5\n")
    model_with_data.import_annotations(csv, description=None)
    annots = model_with_data.current["data"].annotations
    assert annots.description[0] == "annotation"


def test_import_annotations_in_samples(model_with_data, tmp_path):
    """When unit='samples', onset and duration are divided by sfreq."""
    fs = model_with_data.current["data"].info["sfreq"]  # 256 Hz
    csv = tmp_path / "samples.csv"
    _write_annotations_csv(csv, [("BAD", int(1.0 * fs), int(0.5 * fs))])
    model_with_data.import_annotations(csv, unit="samples")
    annots = model_with_data.current["data"].annotations
    assert len(annots) == 1
    np.testing.assert_allclose(annots.onset, [1.0], rtol=1e-6)
    np.testing.assert_allclose(annots.duration, [0.5], rtol=1e-6)


def test_import_annotations_in_samples_no_type_column(model_with_data, tmp_path):
    """unit='samples' works with two-column files as well."""
    fs = model_with_data.current["data"].info["sfreq"]
    csv = tmp_path / "samples_no_type.csv"
    with open(csv, "w") as f:
        f.write("onset,duration\n")
        f.write(f"{int(2.0 * fs)},{int(1.0 * fs)}\n")
    model_with_data.import_annotations(csv, description="STIM", unit="samples")
    annots = model_with_data.current["data"].annotations
    assert len(annots) == 1
    assert annots.description[0] == "STIM"
    np.testing.assert_allclose(annots.onset, [2.0], rtol=1e-6)
    np.testing.assert_allclose(annots.duration, [1.0], rtol=1e-6)


@pytest.fixture
def model_two_datasets(tmp_path):
    """Model with two EDF files loaded (indices 0 and 1)."""
    fs = 256
    model = Model()
    for i in range(2):
        path = tmp_path / f"file_{i}.edf"
        signal = np.zeros(30 * fs)
        Edf([EdfSignal(signal, sampling_frequency=fs, label="EEG")]).write(path)
        model.load(path)
    model.index = 0
    return model


def test_evict_dataset(model_two_datasets):
    """Evicting a dataset sets data to None and writes a temp cache file."""
    model = model_two_datasets
    model.evict_dataset(0)

    assert model.data[0]["data"] is None
    cache = model.data[0]["_cache_path"]
    assert cache is not None
    assert Path(cache).exists()


def test_reload_dataset(model_two_datasets):
    """Reloading a dataset restores its data and keeps the cache path."""
    model = model_two_datasets
    model.evict_dataset(0)
    cache_before = model.data[0]["_cache_path"]

    model.reload_dataset(0)

    assert model.data[0]["data"] is not None
    # cache path is preserved so a second eviction can skip the write
    assert model.data[0]["_cache_path"] == cache_before


def test_evict_twice_reuses_cache(model_two_datasets):
    """A second eviction after a reload reuses the existing cache file."""
    model = model_two_datasets
    model.evict_dataset(0)
    first_cache = model.data[0]["_cache_path"]

    model.reload_dataset(0)
    model.evict_dataset(0)

    assert model.data[0]["_cache_path"] == first_cache


def test_cache_invalidated_after_modify(model_two_datasets):
    """Modifying a reloaded dataset invalidates the cache path."""
    model = model_two_datasets
    model.evict_dataset(0)
    model.reload_dataset(0)
    old_cache = model.data[0]["_cache_path"]

    model.index = 0
    model.crop(0, 5)  # modifying op — invalidates cache

    assert model.current["_cache_path"] is None
    # old temp file is kept on disk (MNE holds a reference to it); cleanup() removes it
    assert Path(old_cache).exists()

    # a fresh eviction now must write a new cache
    model.evict_dataset(0)
    new_cache = model.data[0]["_cache_path"]
    assert new_cache is not None
    assert new_cache != old_cache
    assert Path(new_cache).exists()


def test_cleanup_removes_temp_files(model_two_datasets):
    """cleanup() deletes all temporary cache files."""
    model = model_two_datasets
    model.evict_dataset(0)
    cache = model.data[0]["_cache_path"]
    assert Path(cache).exists()

    model.cleanup()

    assert not Path(cache).exists()
    assert len(model._temp_files) == 0


def test_nbytes_skips_evicted_datasets(model_two_datasets):
    """nbytes does not crash when some datasets are evicted."""
    model = model_two_datasets
    full_bytes = model.nbytes
    model.evict_dataset(0)
    # nbytes should equal only the in-memory dataset
    assert model.nbytes < full_bytes
    assert model.nbytes > 0
