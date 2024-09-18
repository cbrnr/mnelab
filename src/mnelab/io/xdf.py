import struct
import xml.etree.ElementTree as ETree
from collections import defaultdict

import mne
import numpy as np
import scipy.signal
from mne.io import BaseRaw, get_channel_type_constants
from pyxdf import load_xdf
from pyxdf.pyxdf import _read_varlen_int, open_xdf


class RawXDF(BaseRaw):
    """Raw data from .xdf file."""

    def __init__(
        self, fname, stream_ids, marker_ids=None, prefix_markers=False, fs_new=None
    ):
        """Read raw data from .xdf file.

        Parameters
        ----------
        fname : str
            File name to load.
        stream_ids : list[int]
            IDs of streams to load. A list of available streams can be obtained with
            `pyxdf.resolve_streams(fname)`.
        marker_ids : list[int] | None
            IDs of marker streams to load. If `None`, load all marker streams. A marker
            stream is a stream with a nominal sampling frequency of 0 Hz.
        prefix_markers : bool
            Whether to prefix marker streams with their corresponding stream ID.
        fs_new : float | None
            Resampling target frequency in Hz. If only one stream_id is given, this can be
            `None`, in which case no resampling is performed.
        """
        if len(stream_ids) > 1 and fs_new is None:
            raise ValueError("Argument `fs_new` required when reading multiple streams.")

        streams, _ = load_xdf(fname)
        streams = {stream["info"]["stream_id"]: stream for stream in streams}

        if all(_is_markerstream(streams[stream_id]) for stream_id in stream_ids):
            raise RuntimeError(
                "Loading only marker streams is not supported, at least one stream must be "
                "a regular stream."
            )

        labels_all, types_all, units_all = [], [], []
        channel_types = get_channel_type_constants(True)
        for stream_id in stream_ids:
            stream = streams[stream_id]

            n_chans = int(stream["info"]["channel_count"][0])
            labels, types, units = [], [], []
            try:
                for ch in stream["info"]["desc"][0]["channels"][0]["channel"]:
                    labels.append(str(ch["label"][0]))
                    if ch["type"] and ch["type"][0].lower() in channel_types:
                        types.append(ch["type"][0].lower())
                    else:
                        types.append("misc")
                    units.append(ch["unit"][0] if ch["unit"] else "NA")
            except (TypeError, IndexError):  # no channel labels found
                pass
            if not labels:
                labels = [f"{stream['info']['name'][0]}_{n}" for n in range(n_chans)]
            if not units:
                units = ["NA" for _ in range(n_chans)]
            if not types:
                types = ["misc" for _ in range(n_chans)]
            labels_all.extend(labels)
            types_all.extend(types)
            units_all.extend(units)

        if fs_new is not None:
            data, first_time = _resample_streams(streams, stream_ids, fs_new)
            fs = fs_new
        else:  # only possible if a single stream was selected
            data = streams[stream_ids[0]]["time_series"]
            first_time = streams[stream_ids[0]]["time_stamps"][0]
            fs = float(np.array(stream["info"]["effective_srate"]).item())

        info = mne.create_info(ch_names=labels_all, sfreq=fs, ch_types=types_all)

        microvolts = ("microvolt", "microvolts", "µV", "μV", "uV")
        scale = np.array([1e-6 if u in microvolts else 1 for u in units_all])
        data = (data * scale).T

        super().__init__(preload=data, info=info, filenames=[fname])

        # convert marker streams to annotations
        for stream_id, stream in streams.items():
            if marker_ids is not None and stream_id not in marker_ids:
                continue
            if not _is_markerstream(stream):
                continue
            onsets = stream["time_stamps"] - first_time
            prefix = f"{stream_id}-" if prefix_markers else ""
            descriptions = [
                f"{prefix}{item}" for sub in stream["time_series"] for item in sub
            ]
            self.annotations.append(onsets, [0] * len(onsets), descriptions)


def _resample_streams(streams, stream_ids, fs_new):
    """
    Resample multiple XDF streams to a given frequency.

    Parameters
    ----------
    streams : dict
        A dictionary mapping stream IDs to XDF streams.
    stream_ids : list[int]
        The IDs of the desired streams.
    fs_new : float
        Resampling target frequency in Hz.

    Returns
    -------
    all_time_series : np.ndarray
        Array of shape (n_samples, n_channels) containing raw data. Time intervals where a
        stream has no data contain `np.nan`.
    first_time : float
        Time of the very first sample in seconds.
    """
    start_times = []
    end_times = []
    n_total_chans = 0
    for stream_id in stream_ids:
        start_times.append(streams[stream_id]["time_stamps"][0])
        end_times.append(streams[stream_id]["time_stamps"][-1])
        n_total_chans += int(streams[stream_id]["info"]["channel_count"][0])
    first_time = min(start_times)
    last_time = max(end_times)

    n_samples = int(np.ceil((last_time - first_time) * fs_new))
    all_time_series = np.full((n_samples, n_total_chans), np.nan)

    col_start = 0
    for stream_id in stream_ids:
        start_time = streams[stream_id]["time_stamps"][0]
        end_time = streams[stream_id]["time_stamps"][-1]
        len_new = int(np.ceil((end_time - start_time) * fs_new))

        x_old = streams[stream_id]["time_series"]
        x_new = scipy.signal.resample(x_old, len_new, axis=0)

        row_start = int(
            np.floor((streams[stream_id]["time_stamps"][0] - first_time) * fs_new)
        )
        row_end = row_start + x_new.shape[0]
        col_end = col_start + x_new.shape[1]
        all_time_series[row_start:row_end, col_start:col_end] = x_new

        col_start += x_new.shape[1]

    return all_time_series, first_time


def read_raw_xdf(
    fname, stream_ids, marker_ids=None, prefix_markers=False, fs_new=None, *args, **kwargs
):
    """Read XDF file.

    Parameters
    ----------
    fname : str
        File name to load.
    stream_ids : list[int]
        IDs of streams to load. A list of available streams can be obtained with
        `pyxdf.resolve_streams(fname)`.
    marker_ids : list[int] | None
        IDs of marker streams to load. If `None`, load all marker streams. A marker stream
        is a stream with a nominal sampling frequency of 0 Hz.
    prefix_markers : bool
        Whether to prefix marker streams with their corresponding stream ID.
    fs_new : float | None
        Resampling target frequency in Hz. If only one stream_id is given, this can be
        `None`, in which case no resampling is performed.

    Returns
    -------
    RawXDF
        The raw data.
    """

    return RawXDF(fname, stream_ids, marker_ids, prefix_markers, fs_new)


def _is_markerstream(stream):
    srate = float(stream["info"]["nominal_srate"][0])
    n_chans = int(stream["info"]["channel_count"][0])
    return srate == 0 and n_chans == 1


def get_xml(fname):
    """Get XML stream headers and footers from all streams.

    Parameters
    ----------
    fname : str
        Name of the XDF file.

    Returns
    -------
    xml : dict
        XML stream headers and footers.
    """
    with open_xdf(fname) as f:
        xml = defaultdict(dict)
        while True:
            try:
                nbytes = _read_varlen_int(f)
            except EOFError:
                return xml
            tag = struct.unpack("<H", f.read(2))[0]
            if tag in [2, 3, 4, 6]:
                stream_id = struct.unpack("<I", f.read(4))[0]
                if tag in [2, 6]:  # parse StreamHeader/StreamFooter chunk
                    string = f.read(nbytes - 6).decode()
                    xml[stream_id][tag] = ETree.fromstring(string)
                else:  # skip remaining chunk contents
                    f.seek(nbytes - 6, 1)
            else:
                f.seek(nbytes - 2, 1)  # skip remaining chunk contents


def list_chunks(fname):
    """List all chunks contained in an XDF file.

    Listing chunks summarizes the content of the XDF file. Because this function does not
    attempt to parse the data, this also works for corrupted files.

    Parameters
    ----------
    fname : str
        Name of the XDF file.

    Returns
    -------
    chunks : list
        List of dicts containing a short summary for each chunk.
    """
    with open_xdf(fname) as f:
        chunks = []
        while True:
            try:
                nbytes = _read_varlen_int(f)
            except EOFError:
                return chunks
            chunk = {"nbytes": nbytes}
            tag = struct.unpack("<H", f.read(2))[0]
            chunk["tag"] = tag
            if tag == 1:
                chunk["content"] = f.read(nbytes - 2).decode()
            elif tag == 5:
                chunk["content"] = (
                    "0x43 0xA5 0x46 0xDC 0xCB 0xF5 0x41 0x0F "
                    "0xB3 0x0E 0xD5 0x46 0x73 0x83 0xCB 0xE4"
                )
                f.seek(chunk["nbytes"] - 2, 1)  # skip remaining chunk contents
            elif tag in [2, 6]:  # XML
                chunk["stream_id"] = struct.unpack("<I", f.read(4))[0]
                chunk["content"] = f.read(chunk["nbytes"] - 6).decode().replace("\t", "  ")
            elif tag == 4:
                chunk["stream_id"] = struct.unpack("<I", f.read(4))[0]
                collection_time = struct.unpack("<d", f.read(8))[0]
                offset_value = struct.unpack("<d", f.read(8))[0]
                chunk["content"] = (
                    f"Collection time: {collection_time}\n" f"Offset value: {offset_value}"
                )
            elif tag == 3:
                chunk["stream_id"] = struct.unpack("<I", f.read(4))[0]
                remainder = chunk["nbytes"] - 6
                chunk["content"] = f"<BINARY DATA ({remainder} Bytes)>"
                f.seek(remainder, 1)  # skip remaining chunk contents
            else:
                f.seek(chunk["nbytes"] - 2, 1)  # skip remaining chunk contents
            chunks.append(chunk)
