import numpy as np
import pytest

from mnelab.utils import annotations_between_events


@pytest.fixture
def sample_events():
    """Create an events array for testing."""
    # Format: [sample, 0, event_id]
    return np.array([[100, 0, 1], [200, 0, 2], [500, 0, 1], [600, 0, 2]])


def test_simple_pairing(sample_events):
    """Tests interval annotation creation with simple start/end event pairing."""
    annots = annotations_between_events(
        events=sample_events,
        sfreq=100.0,
        start_events=[1],
        end_events=[2],
        annotation="Bad Segment",
        extend_start=False,
        extend_end=False,
    )

    assert len(annots) == 2
    assert annots.description[0] == "Bad Segment"
    assert annots.description[1] == "Bad Segment"

    assert annots.onset[0] == pytest.approx(1.0)
    assert annots.duration[0] == pytest.approx(1.0)

    assert annots.onset[1] == pytest.approx(5.0)
    assert annots.duration[1] == pytest.approx(1.0)


@pytest.mark.parametrize(
    "start_off, end_off, expected_onset, expected_dur",
    [
        (0.0, 0.0, 1.0, 1.0),
        (0.1, 0.0, 1.1, 0.9),
        (0.0, 0.2, 1.0, 1.2),
        (-0.1, 0.1, 0.9, 1.2),
        (0.1, -0.1, 1.1, 0.8),
        (-0.1, -0.1, 0.9, 1.0),
    ],
)
def test_offsets(sample_events, start_off, end_off, expected_onset, expected_dur):
    """Tests interval annotation creation with start/end offsets."""
    events = sample_events[:2]
    annots = annotations_between_events(
        events=events,
        sfreq=100.0,
        start_events=[1],
        end_events=[2],
        annotation="Test",
        start_offset=start_off,
        end_offset=end_off,
        extend_start=False,
        extend_end=False,
    )

    assert annots.onset[0] == pytest.approx(expected_onset)
    assert annots.duration[0] == pytest.approx(expected_dur)


def test_extend_flags(sample_events):
    """Tests interval annotation creation with extend_start and extend_end flags."""
    events = sample_events[:2]
    annots = annotations_between_events(
        events=events,
        sfreq=100.0,
        start_events=[1],
        end_events=[2],
        annotation="Bad Segment",
        max_time=10.0,
        extend_start=True,
        extend_end=True,
    )

    assert len(annots) == 3

    assert annots.onset[0] == 0.0
    assert annots.duration[0] == 1.0

    assert annots.onset[1] == 1.0
    assert annots.duration[1] == 1.0

    assert annots.onset[2] == 2.0
    assert annots.duration[2] == 8.0


def test_interleaved_event():
    """Tests interval annotation creation with interleaved start events."""
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
        sfreq=100.0,
        start_events=[1],
        end_events=[2],
        annotation="Bad Segment",
        extend_start=False,
        extend_end=False,
    )

    assert len(annots) == 1

    assert annots.onset[0] == pytest.approx(1.0)
    assert annots.duration[0] == pytest.approx(2.0)


def test_no_matching_events(sample_events):
    """Tests behavior when no matching start or end events are found."""

    events = sample_events[:1]
    annots = annotations_between_events(
        events=events,
        sfreq=100.0,
        start_events=[1],
        end_events=[2],
        annotation="Bad Segment",
        extend_start=False,
        extend_end=False,
    )

    assert len(annots) == 0


def test_negative_duration(sample_events):
    """Tests that negative duration intervals are not created."""
    events = sample_events[:2]

    annots = annotations_between_events(
        events=events,
        sfreq=100.0,
        start_events=[1],
        end_events=[2],
        annotation="Bad Segment",
        start_offset=2.0,
        extend_start=False,
        extend_end=False,
    )

    assert len(annots) == 0


def test_multiple_events():
    """Tests interval annotation creation with multiple events."""
    events = np.array(
        [
            [100, 0, 4],
            [200, 0, 2],
            [300, 0, 3],
            [400, 0, 1],
            [500, 0, 3],
            [600, 0, 4],
            [700, 0, 1],
            [800, 0, 1],
            [900, 0, 2],
            [1000, 0, 1],
        ]
    )
    annots = annotations_between_events(
        events=events,
        sfreq=100.0,
        start_events=[2, 3, 4],
        end_events=[1],
        annotation="Bad Segment",
        extend_start=False,
        extend_end=False,
    )

    assert len(annots) == 3

    assert annots.onset[0] == pytest.approx(1.0)
    assert annots.duration[0] == pytest.approx(3.0)

    assert annots.onset[1] == pytest.approx(5.0)
    assert annots.duration[1] == pytest.approx(2.0)

    assert annots.onset[2] == pytest.approx(9.0)
    assert annots.duration[2] == pytest.approx(1.0)
