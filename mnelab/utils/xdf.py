import struct
import xml.etree.ElementTree as ET
import numpy as np
import mne


def read_raw_xdf(fname, stream_id):
    """Read XDF file.

    Parameters
    ----------
    fname : str
        Name of the XDF file.
    stream_id : int
        ID (number) of the stream to load.

    Returns
    -------
    raw : mne.io.Raw
        XDF file data.
    """
    from pyxdf import load_xdf

    streams, header = load_xdf(fname)
    for stream in streams:
        if stream["info"]["stream_id"] == stream_id:
            break  # stream found

    n_chans = int(stream["info"]["channel_count"][0])
    fs = float(stream["info"]["nominal_srate"][0])
    labels, types, units = [], [], []
    if stream["info"]["desc"]:
        for ch in stream["info"]["desc"][0]["channels"][0]["channel"]:
            labels.append(str(ch["label"][0]))
            if ch["type"]:
                types.append(ch["type"][0])
            if ch["unit"]:
                units.append(ch["unit"][0])
    if not labels:
        labels = [str(n) for n in range(n_chans)]
    if not units:
        units = ["NA" for _ in range(n_chans)]
    info = mne.create_info(ch_names=labels, sfreq=fs, ch_types="eeg")
    # convert from microvolts to volts if necessary
    scale = np.array([1e-6 if u == "microvolts" else 1 for u in units])
    raw = mne.io.RawArray((stream["time_series"] * scale).T, info)

    first_samp = stream["time_stamps"][0]
    markers = match_streaminfos(resolve_streams(fname), [{"type": "Markers"}])
    for stream_id in markers:
        for stream in streams:
            if stream["info"]["stream_id"] == stream_id:
                break
        onsets = stream["time_stamps"] - first_samp
        descriptions = [item for sub in stream["time_series"] for item in sub]
        raw.annotations.append(onsets, [0] * len(onsets), descriptions)

    return raw


def parse_xdf(fname):
    """Parse and return chunks contained in an XDF file.

    Parameters
    ----------
    fname : str
        Name of the XDF file.

    Returns
    -------
    chunks : list
        List of all chunks contained in the XDF file.
    """
    chunks = []
    with open(fname, "rb") as f:
        if f.read(4) != b"XDF:":  # magic code
            raise ValueError(f"Invalid XDF file {fname}.")
        for chunk in _read_chunks(f):
            chunks.append(chunk)
    return chunks


def parse_chunks(chunks):
    """Parse chunks and extract information on individual streams."""
    streams = []
    for chunk in chunks:
        if chunk["tag"] == 2:  # stream header chunk
            streams.append(dict(stream_id=chunk["stream_id"],
                                name=chunk.get("name"),  # optional
                                type=chunk.get("type"),  # optional
                                channel_count=int(chunk["channel_count"]),
                                channel_format=chunk["channel_format"],
                                nominal_srate=int(chunk["nominal_srate"])))
    return streams


def match_streaminfos(stream_infos, parameters):
    """Find stream IDs matching specified criteria.

    Parameters
    ----------
    stream_infos : list of dicts
        List of dicts containing information on each stream. This information
        can be obtained using the function resolve_streams.
    parameters : list of dicts
        List of dicts containing key/values that should be present in streams.
        Examples: [{"name": "Keyboard"}] matches all streams with a "name"
                  field equal to "Keyboard".
                  [{"name": "Keyboard"}, {"type": "EEG"}] matches all streams
                  with a "name" field equal to "Keyboard" and all streams with
                  a "type" field equal to "EEG".
    """
    matches = []
    for request in parameters:
        for info in stream_infos:
            for key in request.keys():
                match = info[key] == request[key]
                if not match:
                    break
            if match:
                matches.append(info['stream_id'])

    return list(set(matches))  # return unique values


def resolve_streams(fname):
    """Resolve streams in given XDF file.

    Parameters
    ----------
    fname : str
        Name of the XDF file.

    Returns
    -------
    stream_infos : list of dicts
        List of dicts containing information on each stream.
    """
    return parse_chunks(parse_xdf(fname))


def _read_chunks(f):
    """Read and yield XDF chunks.

    Parameters
    ----------
    f : file handle
        File handle of XDF file.


    Yields
    ------
    chunk : dict
        XDF chunk.
    """
    while True:
        chunk = dict()
        try:
            nbytes = struct.unpack("B", f.read(1))[0]
        except struct.error:
            return  # reached EOF
        if nbytes == 1:
            chunk["nbytes"] = struct.unpack("B", f.read(1))[0]
        elif nbytes == 4:
            chunk["nbytes"] = struct.unpack("<I", f.read(4))[0]
        elif nbytes == 8:
            chunk["nbytes"] = struct.unpack("<Q", f.read(8))[0]
        chunk["tag"] = struct.unpack('<H', f.read(2))[0]
        if chunk["tag"] in [2, 3, 4, 6]:
            chunk["stream_id"] = struct.unpack("<I", f.read(4))[0]
            if chunk["tag"] == 2:  # parse StreamHeader chunk
                xml = ET.fromstring(f.read(chunk["nbytes"] - 6).decode())
                chunk = {**chunk, **_parse_streamheader(xml)}
            else:  # skip remaining chunk contents
                f.seek(chunk["nbytes"] - 6, 1)
        else:
            f.seek(chunk["nbytes"] - 2, 1)  # skip remaining chunk contents
        yield chunk


def _parse_streamheader(xml):
    """Parse stream header XML."""
    return {el.tag: el.text for el in xml if el.tag != "desc"}
