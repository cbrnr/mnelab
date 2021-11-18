from collections import defaultdict
import struct
import xml.etree.ElementTree as ETree

import numpy as np
import mne


def read_raw_xdf(fname, stream_id, srate="effective", prefix_markers=False, *args,
                 **kwargs):
    """Read XDF file.

    Parameters
    ----------
    fname : str
        Name of the XDF file.
    stream_id : int
        ID (number) of the stream to load.
    srate : {"nominal", "effective"}
        Use either nominal or effective sampling rate.
    prefix_markers : bool
        Whether or not to prefix markers with their corresponding stream ID.

    Returns
    -------
    raw : mne.io.Raw
        XDF file data.
    """
    from pyxdf import load_xdf, match_streaminfos, resolve_streams

    if srate not in ("nominal", "effective"):
        raise ValueError(f"The 'srate' parameter must be either 'nominal' or 'effective' "
                         f"(got {srate}).")

    streams, _ = load_xdf(fname)
    for stream in streams:
        if stream["info"]["stream_id"] == stream_id:
            break  # stream found
    else:  # stream not found
        raise IOError(f"Stream ID {stream_id} not found.")
    if float(stream["info"]["nominal_srate"][0]) == 0:
        raise RuntimeError("Importing a marker stream is not supported, try importing a "
                           "regularly sampled stream instead.")

    n_chans = int(stream["info"]["channel_count"][0])
    fs = float(np.array(stream["info"][f"{srate}_srate"]).item())
    labels, types, units = [], [], []
    try:
        for ch in stream["info"]["desc"][0]["channels"][0]["channel"]:
            labels.append(str(ch["label"][0]))
            if ch["type"]:
                types.append(ch["type"][0])
            units.append(ch["unit"] if ch["unit"] else "NA")
    except (TypeError, IndexError):  # no channel labels found
        pass
    if not labels:
        labels = [str(n) for n in range(n_chans)]
    if not units:
        units = ["NA" for _ in range(n_chans)]
    info = mne.create_info(ch_names=labels, sfreq=fs, ch_types="eeg")
    # convert from microvolts to volts if necessary
    scale = np.array([1e-6 if u[0] == "microvolts" else 1 for u in units])
    raw = mne.io.RawArray((stream["time_series"] * scale).T, info)
    raw._filenames = [fname]
    first_samp = stream["time_stamps"][0]
    markers = match_streaminfos(resolve_streams(fname), [{"type": "Markers"}])
    for stream_id in markers:
        for stream in streams:
            if stream["info"]["stream_id"] == stream_id:
                break
        onsets = stream["time_stamps"] - first_samp
        prefix = f"{stream_id}-" if prefix_markers else ""
        descriptions = [f"{prefix}{item}" for sub in stream["time_series"] for item in sub]
        raw.annotations.append(onsets, [0] * len(onsets), descriptions)
    return raw


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
    from pyxdf.pyxdf import open_xdf, _read_varlen_int
    with open_xdf(fname) as f:
        xml = defaultdict(dict)
        while True:
            try:
                nbytes = _read_varlen_int(f)
            except EOFError:
                return xml
            tag = struct.unpack('<H', f.read(2))[0]
            if tag in [2, 3, 4, 6]:
                stream_id = struct.unpack("<I", f.read(4))[0]
                if tag in [2, 6]:  # parse StreamHeader/StreamFooter chunk
                    string = f.read(nbytes - 6).decode()
                    xml[stream_id][tag] = ETree.fromstring(string)
                else:  # skip remaining chunk contents
                    f.seek(nbytes - 6, 1)
            else:
                f.seek(nbytes - 2, 1)  # skip remaining chunk contents


def get_streams(fname):
    from pyxdf.pyxdf import parse_chunks, parse_xdf
    return parse_chunks(parse_xdf(fname))
