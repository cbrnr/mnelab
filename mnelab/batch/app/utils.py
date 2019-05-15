from numpy import arange
import mne
from ...tfr.backend.avg_epochs_tfr import AvgEpochsTFR
from ...tfr.backend.epochs_psd import EpochsPSD
from ...tfr.backend.raw_psd import RawPSD


class ReadFileError(Exception):
    pass


def _read(fname):
    """Custom function for reading file in batch processing."""

    # Try raw
    try:
        raw = mne.io.read_raw_fif(fname, preload=True)
        return raw, 'raw'
    except Exception as e:
        pass

    # Try epochs
    try:
        epochs = mne.read_epochs(fname, preload=True)
        return epochs, 'epochs'
    except Exception as e:
        pass

    # Try evoked
    try:
        evoked = mne.read_evokeds(fname, preload=True)
        return evoked, 'evoked'
    except Exception as e:
        pass

    raise ReadFileError()


# ---------------------------------------------------------------------
def init_avg_tfr(data, tfr_params):
    """Init tfr from parameters"""
    fmin = tfr_params['fmin']
    fmax = tfr_params['fmax']
    step = tfr_params.get('freq_step', 1)
    freqs = arange(fmin, fmax, step)
    if tfr_params['time_window'] is not None:
        n_cycles = tfr_params['time_window'] * freqs
    else:
        n_cycles = tfr_params['n_cycles']
    n_fft = tfr_params.get('n_fft', None)

    return AvgEpochsTFR(
        data, freqs, n_cycles,
        method=tfr_params['method'],
        time_bandwidth=tfr_params.get('time_bandwidth', 4),
        width=tfr_params.get('width', 1),
        n_fft=n_fft)


# ---------------------------------------------------------------------
def init_epochs_psd(data, tfr_params):
    """Initialize the instance of EpochsPSD."""

    if tfr_params['method'] == 'welch':
        n_fft = tfr_params['n_fft']
        return EpochsPSD(
            data,
            fmin=tfr_params['fmin'],
            fmax=tfr_params['fmax'],
            tmin=tfr_params['tmin'],
            tmax=tfr_params['tmax'],
            method='welch',
            n_fft=n_fft,
            n_per_seg=tfr_params.get('n_per_seg', n_fft),
            n_overlap=tfr_params.get('n_overlap', 0))

    if tfr_params['method'] == 'multitaper':
        return EpochsPSD(
            data,
            fmin=tfr_params['fmin'],
            fmax=tfr_params['fmax'],
            tmin=tfr_params['tmin'],
            tmax=tfr_params['tmax'],
            method='multitaper',
            bandwidth=tfr_params.get('bandwidth', 4))


# ---------------------------------------------------------------------
def init_raw_psd(data, tfr_params):
    """Initialize the instance of RawPSD."""

    if tfr_params['method'] == 'multitaper':
        return RawPSD(
            data,
            fmin=tfr_params['fmin'],
            fmax=tfr_params['fmax'],
            tmin=tfr_params['tmin'],
            tmax=tfr_params['tmax'],
            method='welch',
            n_fft=tfr_params.get('n_fft', 2048),
            n_per_seg=tfr_params.get('n_per_seg', 2048),
            n_overlap=tfr_params.get('n_overlap', 0))

    if tfr_params['method'] == 'welch':
        return RawPSD(
            data,
            fmin=tfr_params['fmin'],
            fmax=tfr_params['fmax'],
            tmin=tfr_params['tmin'],
            tmax=tfr_params['tmax'],
            method='multitaper',
            bandwidth=tfr_params.get('bandwidth', 4))
