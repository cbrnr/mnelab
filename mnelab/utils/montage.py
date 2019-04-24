#---------------------------------------------------------------------
def xyz_to_montage(path, kind) :
    """Reads and convert xyz positions to a mne montage type"""
    from mne.channels import Montage
    import numpy as np

    n = int(open(path).readline().split(' ')[0])
    coord = np.loadtxt(path, skiprows = 1, usecols = (0,1,2), max_rows = n)
    names = np.loadtxt(path, skiprows = 1, usecols = 3, max_rows = n,
                       dtype = np.dtype(str))
    names = names.tolist()
    return Montage(coord, names, kind,
                   selection = [i for i in range(n)])
