import struct
import xml.etree.ElementTree as ET


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
