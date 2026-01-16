# © MNELAB developers
#
# License: BSD (3-clause)

from textwrap import dedent

from mnelab.utils import format_code
from mnelab.utils.syntax import _remove_unused_imports

expected_formatted_code = """import mne

from mnelab.io import read_raw
from mnelab.utils import annotations_between_events

datasets = []
mne.viz.set_browser_backend("Qt")

data = read_raw("test.bdf", preload=True)
datasets.insert(0, data)
events = mne.find_events(
    data, stim_channel="Status", initial_event=True, uint_cast=True
)
annotations = annotations_between_events(
    events=events,
    sfreq=data.info["sfreq"],
    start_events=[2],
    end_events=[3],
    annotation="BAD_SEGMENT",
    max_time=data.times[-1],
    start_offset=0.0,
    end_offset=0.0,
    extend_start=True,
    extend_end=True,
)
"""

unformatted_code = """from deepcopy import copy
import mne

from mnelab.utils import annotations_between_events
from mnelab.io import read_raw


datasets = []
mne.viz.set_browser_backend('Qt')

data = read_raw("test.bdf", preload=True)
datasets.insert(0, data)
events = mne.find_events(data, stim_channel="Status", initial_event=True, uint_cast=True)
annotations = annotations_between_events(events=events,
                                         sfreq=data.info["sfreq"],
                                         start_events=[2],
                                         end_events=[3],
                                         annotation="BAD_SEGMENT",
                                         max_time=data.times[-1],
                                         start_offset=0.0,
                                         end_offset=0.0,
                                         extend_start=True,
                                         extend_end=True)
"""  # noqa: E501


def test_format_code():
    formatted_code = format_code(unformatted_code)
    assert formatted_code == expected_formatted_code

    invalid_code = "x = print(Hello'J)"
    formatted_code = format_code(invalid_code)
    assert formatted_code == invalid_code  # invalid code should be returned unmodified


def test_remove_unused_imports_keeps_called_functions():
    """Test that function calls are recognized as used imports."""
    code = dedent(
        """
        import mne
        from mnelab.utils.iclabel import run_iclabel

        data = mne.io.read_raw_fif("test.fif")
        probs = run_iclabel(data, None)
        """
    )
    result = _remove_unused_imports(code)
    assert "run_iclabel" in result
    assert "import mne" in result


def test_remove_unused_imports_removes_unused():
    """Test that genuinely unused imports are removed."""
    code = dedent(
        """
        import mne
        import numpy as np
        from mnelab.utils.iclabel import run_iclabel

        data = mne.io.read_raw_fif("test.fif")
        probs = run_iclabel(data, None)
        """
    )
    result = _remove_unused_imports(code)
    assert "numpy" not in result
    assert "run_iclabel" in result
    assert "import mne" in result


def test_remove_unused_imports_mixed_line():
    """Test that lines with mixed used/unused imports are kept."""
    code = dedent(
        """
        import mne
        from mnelab.utils import annotations_between_events, run_iclabel

        data = mne.io.read_raw_fif("test.fif")
        probs = run_iclabel(data, None)
        """
    )
    result = _remove_unused_imports(code)

    assert "annotations_between_events" not in result
    assert "run_iclabel" in result
    assert "from mnelab.utils import run_iclabel" in result
    assert "import mne" in result
