import matplotlib.pyplot as plt
from numpy import mean, log


class EpochsPSD:
    """
    This class contains the PSD of a set of Epochs. It stores the data of
    the psds of each epoch. The psds are calculated with the Library mne.

    Attributes
    ============
    fmin        (float)        : frequency limit

    fmax        (float)        : frequency limit

    tmin        (float)        : lower time bound for each epoch

    tmax        (float)        : higher time bound for each epoch

    info        (mne Infos)    : info of the epochs

    method      (str)          : method used for PSD (multitaper or welch)

    data        (numpy arr.)   : dataset with all the psds data of size
                                  (n_epochs, n_channels, n_freqs)

    freqs       (arr.)         : list containing the frequencies of the psds

    Methods
    =========
    __init__                   : Compute all the PSD of each epoch

    plot_topomap               : Plot the map of the power for a given
                                  frequency and epoch

    plot_topomap_band          : Plot the map of the power for a given band
                                  frequency and epoch

    plot_avg_topomap_band      : Plot the map of the power for a given band,
                                  averaged over epochs

    plot_avg_matrix            : Plot the raw matrix

    plot_avg                   : Plot the matrix for a given epoch

    plot_single_psd            : Plot the PSD for a given epoch and channel

    plot_single_avg_psd        : Plot the PSD averaged over epochs for a given
                                  channel
    """
    def __init__(self, epochs, fmin=0, fmax=1500,
                 tmin=None, tmax=None, type='eeg',
                 method='multitaper', picks=None,
                 **kwargs):
        """
        Computes the PSD of the epochs with the correct method multitaper or
        welch
        """
        from .util import eeg_to_montage

        if type == 'eeg':
            epochs = epochs.copy().pick_types(meg=False, eeg=True)
        if type == 'mag':
            epochs = epochs.copy().pick_types(meg='mag')
        if type == 'grad':
            epochs = epochs.copy().pick_types(meg='grad')
        self.fmin, self.fmax = fmin, fmax
        self.tmin, self.tmax = tmin, tmax
        self.info = epochs.info
        self.method = method
        self.bandwidth = kwargs.get('bandwidth', 4.)
        self.n_fft = kwargs.get('n_fft', 256)
        self.n_per_seg = kwargs.get('n_per_seg', self.n_fft)
        self.n_overlap = kwargs.get('n_overlap', 0)
        self.cmap = 'jet'

        if picks is not None:
            self.picks = picks
        else:
            self.picks = list(range(0, len(epochs.info['ch_names'])))
        for bad in epochs.info['bads']:
            try:
                bad_pick = epochs.info['ch_names'].index(bad)
                self.picks.remove(bad_pick)
            except Exception as e:
                print(e)

        montage = eeg_to_montage(epochs)
        if montage is not None:
            # First we create variable head_pos for a correct plotting
            self.pos = montage.get_pos2d()
            scale = 0.85 / (self.pos.max(axis=0) - self.pos.min(axis=0))
            center = 0.5 * (self.pos.max(axis=0) + self.pos.min(axis=0))
            self.head_pos = {'scale': scale, 'center': center}

            # Handling of possible channels without any known coordinates
            no_coord_channel = False
            try:
                names = montage.ch_names
                indices = [names.index(epochs.info['ch_names'][i])
                           for i in self.picks]
                self.pos = self.pos[indices, :]
            except Exception as e:
                print(e)
                no_coord_channel = True

            # If there is not as much positions as the number of Channels
            # we have to eliminate some channels from the data of topomaps
            if no_coord_channel:
                from mne.channels import read_montage
                from numpy import array

                index = 0
                self.pos = []           # positions
                # index in the self.data of channels with coordinates
                self.with_coord = []

                for i in self.picks:
                    ch_name = epochs.info['ch_names'][i]
                    try:
                        ch_montage = read_montage(
                            montage.kind, ch_names=[ch_name])
                        coord = ch_montage.get_pos2d()
                        self.pos.append(coord[0])
                        self.with_coord.append(index)
                    except Exception as e:
                        print(e)
                    index += 1
                self.pos = array(self.pos)

            else:
                self.with_coord = [i for i in range(len(self.picks))]

        else:  # If there is no montage available
            self.head_pos = None
            self.with_coord = []

        if method == 'multitaper':
            from mne.time_frequency import psd_multitaper

            self.data, self.freqs = psd_multitaper(
                epochs,
                fmin=fmin,
                fmax=fmax,
                tmin=tmin,
                tmax=tmax,
                normalization='full',
                bandwidth=self.bandwidth,
                picks=self.picks)

        if method == 'welch':
            from mne.time_frequency import psd_welch

            self.data, self.freqs = psd_welch(
                epochs,
                fmin=fmin,
                fmax=fmax,
                tmin=tmin,
                tmax=tmax,
                n_fft=self.n_fft,
                n_overlap=self.n_overlap,
                n_per_seg=self.n_per_seg,
                picks=self.picks)

    # ------------------------------------------------------------------------
    def __str__(self):
        """Return informations about the instance"""

        string = ('PSD Computed on {} Epochs with method {}.\nParameters: \n'
                  + 'fmin:{}Hz, fmax:{}Hz (with {} frequency points)\n'
                  + 'tmin: {}s, tmax: {}s\n')
        string.format(len(self.info['chs']), self.method,
                      self.fmin, self.fmax, len(self.freqs),
                      self.tmin, self.tmax)
        if self.method == 'welch':
            string = (string + 'n_fft:{}, n_per_seg:{}, n_overlap:{}\n')
            string.format(self.n_fft, self.n_per_seg, self.n_overlap)
        else:
            string = string + 'bandwidth:{}'.format(self.bandwidth)
        return string

    # ------------------------------------------------------------------------
    def recap(self):
        """Returns a quick recap"""

        if self.method == 'welch':
            string = ('Computed with Welch method, '
                      + 'n_fft: {}, n_per_seg: {}, n_overlap: {}\n')
            string.format(self.n_fft, self.n_per_seg, self.n_overlap)
        else:
            string = 'Computed with Multitaper method, bandwidth: {}'
            string.format(self.bandwidth)
        return string

    # ------------------------------------------------------------------------
    def plot_topomap(self, epoch_index, freq_index,
                     axes=None, log_display=False):
        """
        Plot the map of the power for a given frequency chosen by freq_index,
        the frequencyis hence the value self.freqs[freq_index]. This function
        will return an error if the class is not initialized with the
        coordinates of the different electrodes.
        """
        from mne.viz import plot_topomap

        psd_values = self.data[epoch_index, self.with_coord, freq_index]
        if log_display:
            psd_values = 10 * log(psd_values)
        return plot_topomap(psd_values, self.pos, axes=axes,
                            show=False, cmap=self.cmap,
                            head_pos=self.head_pos)

    # ------------------------------------------------------------------------
    def plot_topomap_band(self, epoch_index, freq_index_min, freq_index_max,
                          axes=None, vmin=None, vmax=None,
                          log_display=False):
        """
        Plot the map of the power for a given frequency band chosen by
        freq_index_min and freq_index_max, the frequency is hence the value
        self.freqs[freq_index]. This function will return an error if the
        class is not initialized with the coordinates of the different
        electrodes.
        """
        from mne.viz import plot_topomap

        psd_values = self.data[epoch_index,
                               self.with_coord,
                               freq_index_min: freq_index_max]
        psd_mean = mean(psd_values, axis=1)
        if log_display:
            psd_mean = 10 * log(psd_mean)
        return plot_topomap(psd_mean, self.pos, axes=axes,
                            vmin=vmin, vmax=vmax, show=False,
                            cmap=self.cmap, head_pos=self.head_pos)

    # ------------------------------------------------------------------------
    def plot_avg_topomap_band(self, freq_index_min, freq_index_max,
                              vmin=None, vmax=None, show_names=False,
                              log_display=False, axes=None):
        """
        Plot the map of the average power for a given frequency band chosen
        by freq_index_min and freq_index_max, the frequency is hence the value
        self.freqs[freq_index]. This function will return an error if the
        class is not initialized with the coordinates of the different
        electrodes.
        """
        from mne.viz import plot_topomap

        psd_values = self.data[:, self.with_coord,
                               freq_index_min: freq_index_max]
        psd_mean = mean(psd_values, axis=2)   # average over frequency band
        psd_mean = mean(psd_mean,   axis=0)   # average over epochs
        if log_display:
            psd_mean = 10 * log(psd_mean)
        return plot_topomap(psd_mean, self.pos, axes=axes,
                            vmin=vmin, vmax=vmax, show=False,
                            cmap=self.cmap, head_pos=self.head_pos)

    # ------------------------------------------------------------------------
    def plot_avg_matrix(self, freq_index_min, freq_index_max, axes=None,
                        vmin=None, vmax=None, log_display=False):
        """
        Plot the map of the average power for a given frequency band chosen
        by freq_index_min and freq_index_max, the frequency is hence the value
        self.freqs[freq_index]. This function will return an error if the
        class is not initialized with the coordinates of the different
        electrodes.
        """
        extent = [
            self.freqs[freq_index_min], self.freqs[freq_index_max],
            self.data.shape[1] + 1,                              1
        ]
        mat = mean(self.data[:, :, freq_index_min: freq_index_max], axis=0)
        if log_display:
            mat = 10 * log(mat)
        if axes is not None:
            return axes.matshow(mat, extent=extent, cmap=self.cmap,
                                vmin=vmin, vmax=vmax)
        else:
            return plt.matshow(mat, extent=extent, cmap=self.cmap,
                               vmin=vmin, vmax=vmax)

    # --------------------------------------------------------------------------
    def plot_matrix(self, epoch_index, freq_index_min, freq_index_max,
                    axes=None, vmin=None, vmax=None,
                    log_display=False):
        """
        Plot the map of the average power for a given frequency band chosen
        by freq_index_min and freq_index_max, the frequency is hence the value
        self.freqs[freq_index]. This function will return an error if the
        class is not initialized with the coordinates of the different
        electrodes.
        """
        extent = [
            self.freqs[freq_index_min], self.freqs[freq_index_max],
            self.data.shape[1] + 1,                              1
        ]
        mat = self.data[epoch_index, :, freq_index_min: freq_index_max]
        if log_display:
            mat = 10 * log(mat)
        if axes is not None:
            return axes.matshow(mat, extent=extent, cmap=self.cmap,
                                vmin=vmin, vmax=vmax)
        else:
            return plt.matshow(mat, extent=extent, cmap=self.cmap,
                               vmin=vmin, vmax=vmax)

    # --------------------------------------------------------------------------
    def plot_single_psd(self, epoch_index, channel_index,
                        axes=None, log_display=False):
        """
        Plot a single PSD corresponding to epoch_index and channel_index,
        between the values corresponding to freq_index_max and
        freq_index_min.
        """
        psd = self.data[epoch_index, channel_index, :]
        if log_display:
            psd = 10 * log(psd)
        if axes is not None:
            return axes.plot(self.freqs, psd, linewidth=2)
        else:
            return plt.plot(self.freqs, psd, linewidth=2)

    # --------------------------------------------------------------------------
    def plot_single_avg_psd(self, channel_index,
                            axes=None, log_display=False):
        """
        Plot a single PSD averaged over epochs and corresponding to
        channel_index, between the values corresponding to freq_index_max
        and freq_index_min.
        """
        psd = mean(self.data[:, channel_index, :], axis=0)
        if log_display:
            psd = 10 * log(psd)
        if axes is not None:
            return axes.plot(self.freqs, psd, linewidth=2)
        else:
            return plt.plot(self.freqs, psd, linewidth=2)

    # ------------------------------------------------------------------------
    def plot_all_psd(self, epoch_index, freq_index_min, freq_index_max,
                     axes=None, log_display=False):
        """
        Plot all single PSD in.
        """
        from matplotlib.cm import jet
        from numpy import linspace

        psds = self.data[epoch_index, :, freq_index_min: freq_index_max]
        if log_display:
            psds = 10 * log(psds)
        nchan = len(self.picks)
        colors = jet(linspace(0, 1, nchan))
        for i, c in zip(range(nchan), colors):
            label = self.info['ch_names'][self.picks[i]]
            axes.plot(self.freqs[freq_index_min: freq_index_max],
                      psds[i, :], color=c, label=label,
                      alpha=.5, picker=2, linewidth=2)
        return axes

    # ------------------------------------------------------------------------
    def plot_all_avg_psd(self, freq_index_min, freq_index_max,
                         axes=None, log_display=False):
        """
        Plot all average single PSD in the axes.
        """
        from matplotlib.cm import jet
        from numpy import linspace

        psds = mean(self.data[:, :, freq_index_min: freq_index_max],
                    axis=0)
        if log_display:
            psds = 10 * log(psds)
        nchan = len(self.picks)
        colors = jet(linspace(0, 1, nchan))
        for i, c in zip(range(nchan), colors):
            label = self.info['ch_names'][self.picks[i]]
            axes.plot(self.freqs[freq_index_min: freq_index_max],
                      psds[i, :], color=c, label=label,
                      alpha=.5, picker=2, linewidth=2)
        return axes

    # ------------------------------------------------------------------------
    def channel_index_from_coord(self, x, y):
        """
        Returns the index of the channel with coordinates closest to (x,y).
        """
        from numpy import argmin

        try:
            scale, center = self.head_pos['scale'], self.head_pos['center']
            x, y = x / scale[0] + center[0], y / scale[1] + center[1]
            distances = [(x-xp)**2 + (y-yp)**2 for xp, yp in self.pos]

            index_coord = argmin(distances)
            index = self.with_coord[index_coord]
            return index

        except Exception as e:
            print(e)
            return None

    # ------------------------------------------------------------------------
    def save_avg_matrix_sef(self, path):
        """
        Save the entire matrix in a sef file
        """
        import numpy as np
        import struct

        n_channels = len(self.info['ch_names'])
        num_freq_frames = len(self.freqs)
        freq_step = (self.freqs[-1] - self.freqs[0]) / num_freq_frames
        sfreq = float(1 / freq_step)

        f = open(path, 'wb')
        for car in 'SE01':
            f.write(struct.pack('c', bytes(car, 'ASCII')))
        f.write(struct.pack('I', n_channels))
        f.write(struct.pack('I', 0))
        f.write(struct.pack('I', num_freq_frames))
        f.write(struct.pack('f', sfreq))
        f.write(struct.pack('H', 0))
        f.write(struct.pack('H', 0))
        f.write(struct.pack('H', 0))
        f.write(struct.pack('H', 0))
        f.write(struct.pack('H', 0))
        f.write(struct.pack('H', 0))
        f.write(struct.pack('H', 0))

        for name in self.info['ch_names']:
            n = 0
            for car in name:
                f.write(struct.pack('c', bytes(car, 'ASCII')))
                n += 1
            while n < 8:
                f.write(struct.pack('x'))
                n += 1

        data = self.data.astype(np.float32)
        data = np.reshape(np.mean(data, axis=0),
                          n_channels * num_freq_frames,
                          order='F')
        data.tofile(f)
        f.close()
