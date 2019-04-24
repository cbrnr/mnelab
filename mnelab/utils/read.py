import numpy as np

def read_ep(path, **kwargs) :
    """
    Reads file with format .ep, and returns a mne.io.Raw object containing
    the data.

    Arguments :
    ============
    path : string
        Datapath of the .ep file
    ch_names : array[str], Opt.
        Names of the channels (default EEG(number))
    sfreq : float, Opt.
        Sampling frequency
    montage : Montage class instance, Opt.
        Montage containing coordinates of the channels

    Returns :
    ============
    Instance of mne.io.Raw
    """
    from mne.io import RawArray
    from mne import create_info

    data       = np.genfromtxt(path, unpack = True)
    n_channels = data.shape[0]

    ch_names   = ['EEG{}'.format(i) for i in range(n_channels)]
    sfreq      = 1e3
    ch_types   = ['eeg' for i in range(n_channels)]
    montage    = None

    if kwargs is not None :
        for key, value in kwargs.items() :
            # ch_name argument
            if key == 'ch_names' :
                if len(value) != n_channels :
                    raise ValueError(
                        "length of ch_names is {} whereas n_channel = {}"
                        .format(len(value), n_channels))
                ch_names = value
            # sfreq argument
            elif key == 'sfreq' : sfreq = value
            # montage argument
            elif key == 'montage' : montage = value
            # keyword error
            else :
                raise ValueError(
                    "Incorrect keyword, must be ch_names, sfreq or montage")

    infos = create_info(ch_names = ch_names, sfreq   = sfreq,
                        ch_types = ch_types, montage = montage)
    return RawArray(data, infos)

def read_eph(path, **kwargs) :
    """
    Reads file with format .ep, and returns a mne.io.Raw object containing the
    data.

    Arguments :
    ============
    path : string
        Datapath of the .ep file
    ch_names : array[str], Opt.
        Names of the channels (default EEG(number))
    sfreq : float, Opt.
        Sampling frequency
    montage : Montage class instance, Opt.
        Montage containing coordinates of the channels

    Returns :
    ============
    Instance of mne.io.Raw
    """
    from mne.io import RawArray
    from mne import create_info

    # Read parameters from header
    with open(path, 'r') as file:
        n_channels, n_times, sfreq = file.readline().strip('\n').split(' ')
        n_channels, n_times        = int(n_channels), int(n_times)
    # Read data
    data = np.genfromtxt(path, skip_header = 1, unpack = True)

    ch_names = ['EEG{}'.format(i + 1) for i in range(n_channels)]
    ch_types = ['eeg' for i in range(n_channels)]
    montage  = None

    if kwargs is not None :
        for key, value in kwargs.items() :

            if key == 'ch_names' :
                if len(value) != n_channels :
                    raise ValueError(
                        "length of ch_names is {} whereas n_channel = {}"
                        .format(len(value), n_channels))
                ch_names = value

            elif key == 'montage' : montage = value

            else :
                raise ValueError("Incorrect keyword")

    infos = create_info(ch_names = ch_names, sfreq   = sfreq,
                        ch_types = ch_types, montage = montage)
    return RawArray(data, infos)

def read_sef(path, montage = None) :
    """
    Reads file with format .sef, and returns a mne.io.Raw object containing
    the data.

    Arguments :
    ============
    path : string
        Datapath of the .ep file
    montage : Montage class instance, Opt.
        Montage containing coordinates of the channels

    Returns :
    ============
    Instance of mne.io.Raw
    """
    from mne.io import RawArray
    from mne import create_info
    import struct
    import re

    f = open(path, 'rb')
    #   Read fixed part of the header
    version             = f.read(4).decode('utf-8')
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
    for k in range(n_channels) :
        name = f.read(8).decode('latin-1')
        ch_names.append(re.sub('[^0-9a-zA-Z]+', '', name))

    # Read data
    buffer = np.frombuffer(
        f.read(n_channels * num_time_frames * 8),
        dtype=np.float32,
        count = n_channels * num_time_frames)
    data = np.reshape(buffer, (num_time_frames, n_channels))

    ch_types = ['eeg' for i in range(n_channels)]
    infos = create_info(
        ch_names = ch_names, sfreq   = sfreq,
        ch_types = ch_types, montage = montage)
    return RawArray(np.transpose(data), infos)
