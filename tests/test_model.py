# © MNELAB developers
#
# License: BSD (3-clause)

import math

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

    # @pipeline_step always creates one child; duplicate_data adds a second level
    expected_len = len(edf_files) + (2 if duplicate_data else 1)
    assert len(model.data) == expected_len, (
        "Number of data sets in model is not equal to number of files after appending"
    )

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


def test_pipeline_step_parent_index_consistency(edf_files):
    """Inserting a pipeline step must not corrupt parent_index of other trees.

    Regression test: @pipeline_step used list.insert() without updating the parent_index
    values of existing datasets that were displaced by the insertion.  As a result a
    sibling tree's child could end up parented to the newly inserted node instead of its
    real parent.
    """
    model = Model()
    model.load(edf_files[0])  # Dataset 1 at index 0
    model.load(edf_files[1])  # Dataset 2 at index 1

    # add a step to Dataset 1 (navigate back, then operate)
    model.index = 0
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        model.find_events(stim_channel=model.current["data"].info["ch_names"][0])
    # now: 0=Dataset1, 1=FindEvents1(parent=0), 2=Dataset2

    # add a step to Dataset 2 (navigate there, then operate)
    model.index = 2
    model.find_events(stim_channel=model.current["data"].info["ch_names"][0])
    # now: 0=Dataset1, 1=FindEvents1(parent=0), 2=Dataset2, 3=FindEvents2(parent=2)

    # go back to FindEvents1 and add another step
    model.index = 1
    model.crop(0, 5)
    # should give: 0=D1, 1=FE1, 2=Crop(parent=1), 3=D2, 4=FE2(parent=3)

    # verify Dataset2's subtree is still intact
    tree = model.get_pipeline_tree()
    roots = {node["index"]: node for node in tree}
    assert 0 in roots, "Dataset 1 should be a root"
    assert 3 in roots, "Dataset 2 should be a root"

    d2_children = roots[3]["children"]
    assert len(d2_children) == 1, "Dataset 2 should still have exactly one child"
    assert d2_children[0]["index"] == 4, "FindEvents2 should be child of Dataset 2"
    assert model.data[4].get("parent_index") == 3, (
        "parent_index of FindEvents2 must point to Dataset 2"
    )


def test_pipeline_step_branches_from_intermediate_node(model_with_data):
    """A new step from an intermediate node becomes a sibling branch."""
    model = model_with_data
    model.crop(0, 10)
    first_crop = model.index
    model.crop(0, 2)

    model.index = first_crop
    model.crop(3, 5)

    tree = model.get_pipeline_tree()
    assert len(tree) == 1
    first_branch = tree[0]["children"][0]
    assert first_branch["index"] == first_crop
    assert [child["index"] for child in first_branch["children"]] == [2, 3]
    assert model.data[2].get("parent_index") == first_crop
    assert model.data[3].get("parent_index") == first_crop


def test_remove_data_preserves_active_index_when_possible(model_with_data):
    """Removing unrelated or parent subtrees keeps selection valid."""
    model = model_with_data
    model.crop(0, 10)
    first_crop = model.index
    model.crop(0, 2)

    model.index = first_crop
    model.crop(3, 5)
    active_name = model.current["name"]

    model.remove_data(2)
    assert model.current["name"] == active_name
    assert model.index == 2
    assert model.current.get("parent_index") == 1

    model.remove_data(1)
    assert model.index == 0
    assert len(model.data) == 1


def test_append_data_adjusts_indices_after_subtree_insert(edf_files):
    """Appending can reference descendants before the inserted pipeline child."""
    model = Model()
    for file in edf_files:
        model.load(file)

    root_len = len(model.data[0]["data"].times)
    extra_lens = [len(model.data[i]["data"].times) for i in (1, 2)]

    model.index = 0
    model.crop(0, 1)
    cropped_len = len(model.current["data"].times)

    model.index = 0
    model.append_data([1, 2, 3])

    assert model.index == 2
    assert model.current.get("parent_index") == 0
    assert len(model.current["data"].times) == root_len + cropped_len + sum(extra_lens)
