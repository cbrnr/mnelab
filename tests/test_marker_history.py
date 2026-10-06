# © MNELAB developers
#
# License: BSD (3-clause)

from types import SimpleNamespace

import mne
import numpy as np
import pytest

from mnelab.utils.marker_history import annotations_history, events_history


@pytest.mark.parametrize(
    ("old", "new", "row_ids"),
    [
        (
            [[100, 0, 1], [200, 0, 2]],
            [[100, 0, 3], [150, 0, 1], [200, 0, 2]],
            [2, 0, 1],
        ),
        (
            [[100, 0, 1], [200, 0, 2], [300, 0, 3], [400, 0, 4]],
            [[100, 0, 5], [200, 0, 6], [400, 0, 7]],
            [0, 1, 3],
        ),
        (
            [[100, 0, 1], [200, 0, 2], [300, 0, 3]],
            [[200, 0, 2]],
            [1],
        ),
        (
            [[100, 0, 1], [200, 0, 2], [300, 0, 3]],
            [[50, 0, 2], [100, 0, 1], [300, 0, 3]],
            [1, 0, 2],
        ),
    ],
)
def test_events_history_replays(old, new, row_ids):
    """Event History replays mixed edits without replacing the whole array."""
    old = np.array(old)
    new = np.array(new)
    history = events_history(old, new, row_ids)
    data = SimpleNamespace(events=old.copy())

    exec(history, {"data": data, "np": np})  # noqa: S102

    np.testing.assert_array_equal(data.events, new)
    assert "np.array" not in history
    if row_ids == [1, 0, 2]:
        assert "np.argsort" in history
        assert "[1, 0, 2]" not in history


@pytest.mark.parametrize(
    ("old", "new", "row_ids"),
    [
        (
            ([1.0, 2.0], [0.5, 0.5], ["A", "B"]),
            ([1.0, 1.5, 2.0], [0.0, 0.5, 0.5], ["C", "A", "B"]),
            [2, 0, 1],
        ),
        (
            ([1.0, 2.0, 3.0], [0.5, 0.5, 0.5], ["A", "B", "C"]),
            ([2.0], [0.75], ["LONGER"]),
            [1],
        ),
        (
            ([1.0, 2.0], [0.5, 0.5], ["A", "B"]),
            ([0.5, 1.0], [0.5, 0.5], ["B", "A"]),
            [1, 0],
        ),
    ],
)
def test_annotations_history_replays(old, new, row_ids):
    """Annotation History replays mixed edits without replacing all annotations."""
    data = mne.io.RawArray(np.zeros((1, 100)), mne.create_info(1, 10))
    data.set_annotations(mne.Annotations(*old))
    expected = mne.Annotations(*new)
    history = annotations_history(data.annotations, expected, row_ids)

    exec(history, {"data": data, "mne": mne, "np": np})  # noqa: S102

    np.testing.assert_array_equal(data.annotations.onset, expected.onset)
    np.testing.assert_array_equal(data.annotations.duration, expected.duration)
    np.testing.assert_array_equal(data.annotations.description, expected.description)
    assert "mne.Annotations" not in history
    if row_ids == [1, 0]:
        assert "np.lexsort" in history
        assert "[1, 0]" not in history


def test_annotations_history_replacement_keeps_orig_time():
    """Replacing all annotations of cropped data keeps their times."""
    data = mne.io.RawArray(np.zeros((1, 300)), mne.create_info(1, 10))
    data.set_meas_date(1_700_000_000)
    data.set_annotations(mne.Annotations([15.0, 20.0], [1.0, 1.0], ["A", "B"]))
    data.crop(10, None)
    old = data.annotations.copy()
    expected = mne.Annotations(
        [15.0, 25.0], [1.0, 1.0], ["A", "C"], orig_time=old.orig_time
    )
    history = annotations_history(old, expected, [0, 0])

    exec(history, {"data": data, "mne": mne, "np": np})  # noqa: S102

    assert "mne.Annotations" in history
    np.testing.assert_allclose(data.annotations.onset, expected.onset)
    assert data.annotations.description.tolist() == ["A", "C"]
