def xyz_to_montage(path, kind=''):
    """Reads and convert xyz positions to a mne montage type"""
    from mne.channels import Montage
    import numpy as np

    n = int(open(path).readline().split(' ')[0])
    coord = np.loadtxt(path, skiprows=1, usecols=(0, 1, 2), max_rows=n)
    names = np.loadtxt(path, skiprows=1, usecols=3, max_rows=n,
                       dtype=np.dtype(str))
    names = names.tolist()
    return Montage(coord, names, kind,
                   selection=[i for i in range(n)])


def eeg_to_montage(eeg):
    """Returns an instance of montage from an eeg file"""
    from numpy import array, isnan
    from mne.channels import Montage

    pos = array([eeg.info['chs'][i]['loc'][:3]
                 for i in range(eeg.info['nchan'])])
    if not isnan(pos).all():
        selection = [i for i in range(eeg.info['nchan'])]
        montage = Montage(pos, eeg.info['ch_names'],
                          selection=selection, kind='')
        return montage
    else:
        return None
