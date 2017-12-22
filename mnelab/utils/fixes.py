from mne.io.constants import FIFF


# required for MNE < 0.16
def get_channel_types():
    """Return all known channel types.

    Returns
    -------
    channel_types : dict
        The keys contain the channel types, and the values contain the
        corresponding values in the info['chs'][idx] dictionary.
    """
    return dict(grad=dict(kind=FIFF.FIFFV_MEG_CH,
                          unit=FIFF.FIFF_UNIT_T_M),
                mag=dict(kind=FIFF.FIFFV_MEG_CH,
                         unit=FIFF.FIFF_UNIT_T),
                ref_meg=dict(kind=FIFF.FIFFV_REF_MEG_CH),
                eeg=dict(kind=FIFF.FIFFV_EEG_CH),
                stim=dict(kind=FIFF.FIFFV_STIM_CH),
                eog=dict(kind=FIFF.FIFFV_EOG_CH),
                emg=dict(kind=FIFF.FIFFV_EMG_CH),
                ecg=dict(kind=FIFF.FIFFV_ECG_CH),
                resp=dict(kind=FIFF.FIFFV_RESP_CH),
                misc=dict(kind=FIFF.FIFFV_MISC_CH),
                exci=dict(kind=FIFF.FIFFV_EXCI_CH),
                ias=dict(kind=FIFF.FIFFV_IAS_CH),
                syst=dict(kind=FIFF.FIFFV_SYST_CH),
                seeg=dict(kind=FIFF.FIFFV_SEEG_CH),
                bio=dict(kind=FIFF.FIFFV_BIO_CH),
                chpi=dict(kind=[FIFF.FIFFV_QUAT_0, FIFF.FIFFV_QUAT_1,
                                FIFF.FIFFV_QUAT_2, FIFF.FIFFV_QUAT_3,
                                FIFF.FIFFV_QUAT_4, FIFF.FIFFV_QUAT_5,
                                FIFF.FIFFV_QUAT_6, FIFF.FIFFV_HPI_G,
                                FIFF.FIFFV_HPI_ERR, FIFF.FIFFV_HPI_MOV]),
                dipole=dict(kind=FIFF.FIFFV_DIPOLE_WAVE),
                gof=dict(kind=FIFF.FIFFV_GOODNESS_FIT),
                ecog=dict(kind=FIFF.FIFFV_ECOG_CH),
                hbo=dict(kind=FIFF.FIFFV_FNIRS_CH,
                         coil_type=FIFF.FIFFV_COIL_FNIRS_HBO),
                hbr=dict(kind=FIFF.FIFFV_FNIRS_CH,
                         coil_type=FIFF.FIFFV_COIL_FNIRS_HBR))
