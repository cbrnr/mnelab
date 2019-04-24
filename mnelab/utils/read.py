import numpy as np


def read_sef(path):
    """
    Reads file with format .sef, and returns a mne.io.Raw object containing
    the data.
    """
    from mne.io import RawArray
    from mne import create_info
    import struct
    import re

    f = open(path, 'rb')
    #   Read fixed part of the header
    version = f.read(4).decode('utf-8')
    n_channels,         = struct.unpack('I', f.read(4))
    num_aux_electrodes, = struct.unpack('I', f.read(4))
    num_time_frames,    = struct.unpack('I', f.read(4))
    sfreq,              = struct.unpack('f', f.read(4))
    year,               = struct.unpack('H', f.read(2))
    month,              = struct.unpack('H', f.read(2))
    day,                = struct.unpack('H', f.read(2))
    hour,               = struct.unpack('H', f.read(2))
    minute,             = struct.unpack('H', f.read(2))
    second,             = struct.unpack('H', f.read(2))
    millisecond,        = struct.unpack('H', f.read(2))

    #   Read variable part of the header
    ch_names = []
    for k in range(n_channels):
        name = f.read(8).decode('latin-1')
        ch_names.append(re.sub('[^0-9a-zA-Z]+', '', name))

    # Read data
    buffer = np.frombuffer(
        f.read(n_channels * num_time_frames * 8),
        dtype=np.float32,
        count=n_channels * num_time_frames)
    data = np.reshape(buffer, (num_time_frames, n_channels))

    ch_types = ['eeg' for i in range(n_channels)]
    infos = create_info(
        ch_names=ch_names, sfreq=sfreq,
        ch_types=ch_types)
    return RawArray(np.transpose(data), infos)
