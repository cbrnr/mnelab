from mnelab.utils import format_with_black

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


def test_format_with_black():
    formatted_code = format_with_black(unformatted_code)
    assert formatted_code == expected_formatted_code

    invalid_code = "x = print(Hello'J)"
    formatted_code = format_with_black(invalid_code)
    assert formatted_code == invalid_code  # invalid code should be returned unmodified
