# © MNELAB developers
#
# License: BSD (3-clause)

import numpy as np
import pytest

from mnelab.utils import (
    annotations_between_events,
    get_annotation_types_from_file,
    merge_annotations,
    read_annotations_from_file,
)

SFREQ = 100.0


@pytest.fixture
def events():
    """Create an events array for testing."""
    # Format: [sample, 0, event_id]
    return np.array(
        [[1 * SFREQ, 0, 1], [2 * SFREQ, 0, 2], [5 * SFREQ, 0, 1], [6 * SFREQ, 0, 2]]
    )


def test_simple_pairing(events):
    """Test interval annotation creation with simple start/end event pairing."""
    annots = annotations_between_events(
        events=events,
        sfreq=SFREQ,
        start_events=[1],
        end_events=[2],
        annotation="Bad Segment",
        extend_start=False,
        extend_end=False,
    )

    assert len(annots) == 2
    assert all(d == "Bad Segment" for d in annots.description)

    np.testing.assert_allclose(annots.onset, [1.0, 5.0])
    np.testing.assert_allclose(annots.duration, [1.0, 1.0])


@pytest.mark.parametrize(
    "start_offset, end_offset, expected_onset, expected_duration",
    [
        (0.0, 0.0, 1.0, 1.0),
        (0.1, 0.0, 1.1, 0.9),
        (0.0, 0.2, 1.0, 1.2),
        (-0.1, 0.1, 0.9, 1.2),
        (0.1, -0.1, 1.1, 0.8),
        (-0.1, -0.1, 0.9, 1.0),
    ],
)
def test_offsets(events, start_offset, end_offset, expected_onset, expected_duration):
    """Test interval annotation creation with start/end offsets."""
    annots = annotations_between_events(
        events=events[:2],
        sfreq=SFREQ,
        start_events=[1],
        end_events=[2],
        annotation="Bad Segment",
        start_offset=start_offset,
        end_offset=end_offset,
        extend_start=False,
        extend_end=False,
    )

    np.testing.assert_allclose(annots.onset[0], expected_onset)
    np.testing.assert_allclose(annots.duration[0], expected_duration)


def test_extend_flags(events):
    """Test interval annotation creation with extend_start and extend_end flags."""
    annots = annotations_between_events(
        events=events,
        sfreq=SFREQ,
        start_events=[1],
        end_events=[2],
        annotation="Bad Segment",
        max_time=10.0,
        extend_start=True,
        extend_end=True,
    )
    assert len(annots) == 2

    np.testing.assert_allclose(annots.onset, [0.0, 5.0])
    np.testing.assert_allclose(annots.duration, [2.0, 5.0])


def test_interleaved_event():
    """Test interval annotation creation with interleaved start events."""
    events = np.array(
        [
            [100, 0, 1],
            [200, 0, 1],
            [300, 0, 2],
            [400, 0, 2],
        ]
    )

    annots = annotations_between_events(
        events=events,
        sfreq=SFREQ,
        start_events=[1],
        end_events=[2],
        annotation="Bad Segment",
        extend_start=False,
        extend_end=False,
    )

    assert len(annots) == 1

    np.testing.assert_allclose(annots.onset[0], 1.0)
    np.testing.assert_allclose(annots.duration[0], 2.0)


def test_no_matching_events(events):
    """Test behavior when no matching start or end events are found."""
    annots = annotations_between_events(
        events=events[:1],
        sfreq=SFREQ,
        start_events=[1],
        end_events=[2],
        annotation="Bad Segment",
        extend_start=False,
        extend_end=False,
    )

    assert len(annots) == 0


def test_negative_duration(events):
    """Test that negative duration intervals are not created."""
    annots = annotations_between_events(
        events=events[:2],
        sfreq=SFREQ,
        start_events=[1],
        end_events=[2],
        annotation="Bad Segment",
        start_offset=2.0,
        extend_start=False,
        extend_end=False,
    )

    assert len(annots) == 0


def test_multiple_events():
    """Test interval annotation creation with multiple events."""
    events = np.array(
        [
            [1 * SFREQ, 0, 4],
            [2 * SFREQ, 0, 2],
            [3 * SFREQ, 0, 3],
            [4 * SFREQ, 0, 1],
            [5 * SFREQ, 0, 3],
            [6 * SFREQ, 0, 4],
            [7 * SFREQ, 0, 1],
            [8 * SFREQ, 0, 1],
            [9 * SFREQ, 0, 2],
            [10 * SFREQ, 0, 1],
        ]
    )
    annots = annotations_between_events(
        events=events,
        sfreq=SFREQ,
        start_events=[2, 3, 4],
        end_events=[1],
        annotation="Bad Segment",
        extend_start=False,
        extend_end=False,
    )

    assert len(annots) == 3

    np.testing.assert_allclose(annots.onset, [1.0, 5.0, 9.0])
    np.testing.assert_allclose(annots.duration, [3.0, 2.0, 1.0])


@pytest.mark.parametrize(
    "sfreq",
    [0.0, -100.0, None, "invalid"],
)
def test_invalid_sfreq(events, sfreq):
    """Test that invalid sampling frequency raises an error."""
    with pytest.raises((ValueError, TypeError)):
        annotations_between_events(
            events=events,
            sfreq=sfreq,
            start_events=[1],
            end_events=[2],
            annotation="Bad Segment",
        )


def test_empty_events():
    """Test behavior with empty events array."""
    events = np.array([]).reshape(0, 3)

    annots = annotations_between_events(
        events=events,
        sfreq=SFREQ,
        start_events=[1],
        end_events=[2],
        annotation="Bad Segment",
        extend_start=True,
        extend_end=True,
    )

    assert len(annots) == 0


def test_missing_event_ids(events):
    """Test behavior when start/end events are not in the events array."""
    annots = annotations_between_events(
        events=events,
        sfreq=SFREQ,
        start_events=[99],
        end_events=[999],
        annotation="Bad Segment",
        extend_start=False,
        extend_end=False,
    )

    assert len(annots) == 0


def test_merge_adjacent_events():
    """Test that annotations sharing a sample point are merged."""
    events = np.array(
        [
            [1 * SFREQ, 0, 1],
            [2 * SFREQ, 0, 2],
            [2 * SFREQ, 0, 1],
            [3 * SFREQ, 0, 2],
        ]
    )

    annots = annotations_between_events(
        events=events,
        sfreq=SFREQ,
        start_events=[1],
        end_events=[2],
        annotation="Bad Segment",
        extend_start=False,
        extend_end=False,
    )

    assert len(annots) == 1

    np.testing.assert_allclose(annots.onset, [1.0])
    np.testing.assert_allclose(annots.duration, [2.0])


def test_merge_overlapping_events():
    """Test that overlapping annotations are merged into a single annotation."""
    events = np.array(
        [
            [2 * SFREQ, 0, 1],
            [3 * SFREQ, 0, 2],
            [4 * SFREQ, 0, 1],
            [5 * SFREQ, 0, 2],
        ]
    )

    annots = annotations_between_events(
        events=events,
        sfreq=SFREQ,
        start_events=[1],
        end_events=[2],
        annotation="Bad Segment",
        start_offset=-1.5,
        extend_start=False,
        extend_end=False,
    )

    assert len(annots) == 1
    np.testing.assert_allclose(annots.onset, [0.5])
    np.testing.assert_allclose(annots.duration, [4.5])


def test_clamp_to_min_max_time(events):
    """Test that annotations are clamped to max_time and not starting before 0."""
    annots = annotations_between_events(
        events=events[:2],
        sfreq=SFREQ,
        start_events=[1],
        end_events=[2],
        annotation="Bad Segment",
        start_offset=-2.0,
        end_offset=2.0,
        max_time=4.0,
        extend_start=False,
        extend_end=False,
    )

    assert len(annots) == 1
    np.testing.assert_allclose(annots.onset, [0.0])
    np.testing.assert_allclose(annots.duration, [4.0])


def test_merge_annotations_basic():
    """Test basic merging of adjacent and overlapping intervals."""
    onsets = [1.0, 2.0, 4.0, 5.0, 8.0]
    durations = [1.0, 1.0, 2.0, 2.0, 1.0]
    descriptions = ["A", "A", "B", "B", "A"]

    m_onsets, m_durations, m_descriptions = merge_annotations(
        onsets, durations, descriptions
    )

    np.testing.assert_allclose(m_onsets, [1.0, 4.0, 8.0])
    np.testing.assert_allclose(m_durations, [2.0, 3.0, 1.0])
    assert m_descriptions == ["A", "B", "A"]


def test_merge_annotations_no_merge():
    """Test that non-overlapping and non-adjacent intervals are not merged."""
    onsets = [1.0, 3.0, 6.0]
    durations = [1.0, 1.0, 1.0]
    descriptions = ["A", "B", "A"]

    m_onsets, m_durations, m_descriptions = merge_annotations(
        onsets, durations, descriptions
    )

    np.testing.assert_allclose(m_onsets, onsets)
    np.testing.assert_allclose(m_durations, durations)
    assert m_descriptions == descriptions


def test_merge_annotations_different_descriptions():
    """Test that overlapping intervals with different descriptions are not merged."""
    onsets = [1.0, 2.0]
    durations = [2.0, 2.0]
    descriptions = ["A", "B"]

    m_onsets, m_durations, m_descriptions = merge_annotations(
        onsets, durations, descriptions
    )

    np.testing.assert_allclose(m_onsets, [1.0, 2.0])
    np.testing.assert_allclose(m_durations, [2.0, 2.0])
    assert m_descriptions == ["A", "B"]


def test_merge_annotations_contained_interval():
    """Test that an interval completely contained within another is merged."""
    onsets = [1.0, 1.5]
    durations = [3.0, 1.0]
    descriptions = ["A", "A"]

    m_onsets, m_durations, m_descriptions = merge_annotations(
        onsets, durations, descriptions
    )

    np.testing.assert_allclose(m_onsets, [1.0])
    np.testing.assert_allclose(m_durations, [3.0])
    assert m_descriptions == ["A"]


# --- read_annotations_from_file ---


def test_read_annotations_from_file_three_column(tmp_path):
    """Reads type,onset,duration CSV files as MNE annotations."""
    csv = tmp_path / "annots.csv"
    csv.write_text("type,onset,duration\nBAD,1.0,0.5\nGOOD,2.0,0.25\n")

    annots = read_annotations_from_file(csv, SFREQ, types=["BAD"])

    assert list(annots.description) == ["BAD"]
    np.testing.assert_allclose(annots.onset, [1.0])
    np.testing.assert_allclose(annots.duration, [0.5])


def test_read_annotations_from_file_two_column_samples(tmp_path):
    """Reads onset,duration CSV files and converts samples to seconds."""
    csv = tmp_path / "annots.csv"
    csv.write_text("onset,duration\n100,50\n")

    annots = read_annotations_from_file(csv, SFREQ, description="BAD", unit="samples")

    assert list(annots.description) == ["BAD"]
    np.testing.assert_allclose(annots.onset, [1.0])
    np.testing.assert_allclose(annots.duration, [0.5])


def test_read_annotations_from_file_rejects_invalid_header(tmp_path):
    """Rejects files without a supported annotations CSV header."""
    csv = tmp_path / "bad.csv"
    csv.write_text("bad-header\n")

    with pytest.raises(ValueError, match="Invalid annotations file"):
        read_annotations_from_file(csv, SFREQ)


def test_read_annotations_from_file_rejects_out_of_range_onset(tmp_path):
    """Rejects annotations starting outside the data range."""
    csv = tmp_path / "bad.csv"
    csv.write_text("type,onset,duration\nBAD,999.0,0.5\n")

    with pytest.raises(ValueError, match="outside the data range"):
        read_annotations_from_file(csv, SFREQ, max_time=10.0)


# --- get_annotation_types_from_file ---


def test_get_annotation_types_from_file_three_column(tmp_path):
    """Returns sorted unique types from a type,onset,duration file."""
    csv = tmp_path / "annots.csv"
    csv.write_text("type,onset,duration\nBAD,1.0,0.5\nGOOD,2.0,0.5\nBAD,5.0,1.0\n")
    types, _ = get_annotation_types_from_file(csv)
    assert types == ["BAD", "GOOD"]


def test_get_annotation_types_from_file_two_column_returns_none(tmp_path):
    """Returns None for a file with no type column (onset,duration header)."""
    csv = tmp_path / "no_type.csv"
    csv.write_text("onset,duration\n1.0,0.5\n2.0,1.0\n")
    types, _ = get_annotation_types_from_file(csv)
    assert types is None


# --- integer-value detection ---


def test_check_annotation_values_are_integer_all_integers(tmp_path):
    """Returns True when all onset/duration values are whole numbers."""
    csv = tmp_path / "annots.csv"
    csv.write_text("type,onset,duration\nBAD,256,128\nBAD,512,64\n")
    _, values_are_integer = get_annotation_types_from_file(csv)
    assert values_are_integer is True


def test_check_annotation_values_are_integer_float_integers(tmp_path):
    """Returns True when values are float-encoded whole numbers (e.g. 256.0)."""
    csv = tmp_path / "annots.csv"
    csv.write_text("type,onset,duration\nBAD,256.0,128.0\n")
    _, values_are_integer = get_annotation_types_from_file(csv)
    assert values_are_integer is True


def test_check_annotation_values_are_integer_has_fractions(tmp_path):
    """Returns False when any value has a fractional part."""
    csv = tmp_path / "annots.csv"
    csv.write_text("type,onset,duration\nBAD,1.5,0.5\n")
    _, values_are_integer = get_annotation_types_from_file(csv)
    assert values_are_integer is False


def test_check_annotation_values_are_integer_two_column(tmp_path):
    """Works with two-column (onset,duration) files."""
    csv = tmp_path / "no_type.csv"
    csv.write_text("onset,duration\n100,50\n200,25\n")
    _, values_are_integer = get_annotation_types_from_file(csv)
    assert values_are_integer is True


def test_check_annotation_values_are_integer_empty_file(tmp_path):
    """Returns False when the file has no data rows."""
    csv = tmp_path / "empty.csv"
    csv.write_text("type,onset,duration\n")
    _, values_are_integer = get_annotation_types_from_file(csv)
    assert values_are_integer is False
