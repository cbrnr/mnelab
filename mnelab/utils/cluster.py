import numpy as np
from mne.stats import permutation_cluster_1samp_test as pcluster_test


def cluster_tf_maps(tfr_ev, ch):
    print(f"Computing permutation test for channel {ch}...")
    cluster_params = dict(n_permutations=100, step_down_p=0.05, seed=1,
                          buffer_size=None)  # for cluster test

    # positive clusters
    _, c1, p1, _ = pcluster_test(tfr_ev.data[:, ch, ...],
                                 tail=1, **cluster_params)
    # negative clusters
    _, c2, p2, _ = pcluster_test(tfr_ev.data[:, ch, ...],
                                 tail=-1, **cluster_params)

    c = []
    if bool(len(c1)) and bool(len(c2)):
        c = np.stack(c1 + c2, axis=2)  # combined clusters
    elif bool(len(c1)):
        c = np.swapaxes(c1, 1, 2).T
    elif bool(len(c2)):
        c = np.swapaxes(c2, 1, 2).T

    if len(c) > 0:
        p = np.concatenate((p1, p2))  # combined p-values
        mask = c[..., p <= 0.05].any(axis=-1)
    else:
        tfr_avg = tfr_ev.average()
        mask = np.ones(tfr_avg._data.shape[1:]) == 1

    return mask
