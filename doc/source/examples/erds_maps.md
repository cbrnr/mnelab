# Compute and visualize ERDS maps

Based on [this MNE-Python example](https://mne.tools/dev/auto_examples/time_frequency/time_frequency_erds.html), which also provides a bit of background information on ERDS.

## Download required files
Download data files for runs 6, 10, and 14 of subject 1 from the [EEG Motor Movement/Imagery Dataset](https://physionet.org/content/eegmmidb/1.0.0/):
- [S001R06.edf](https://physionet.org/files/eegmmidb/1.0.0/S001/S001R06.edf?download)
- [S001R10.edf](https://physionet.org/files/eegmmidb/1.0.0/S001/S001R10.edf?download)
- [S001R14.edf](https://physionet.org/files/eegmmidb/1.0.0/S001/S001R14.edf?download)

## Load data sets
In MNELAB, go to `File -> Open...`, select the three downloaded files and click `Open`.
In the sidebar, the three data sets are now visible.
The data set loaded last (`S001R14`) is highlighted, indicating it is currently "active".
Therefore, the info panel shows information about that data set.

## Concatenate data
Now we want to concatenate the three data sets, starting with `S001R06`.
In the sidebar, select `S001R06`, then go to `Edit -> Append data...`.
Select `S001R10` and `S001R14` in the `Source` panel - to select multiple items, hold <kbd>Ctrl</kbd> while clicking.
Drag the selected data sets to the `Destination` panel and confirm with `OK`.
A new entry appears in the sidebar: `S001R06 (appended)`.
The entries `Samples` and `Length` in the info panel confirm that it is the result of the concatenation.
To close the original data sets, select them in the sidebar and go to `File -> Close` (or press <kbd>Ctrl</kbd>+<kbd>F4</kbd>).

## Convert annotations to events
Splitting the raw data into epochs requires _events_.
The info panel shows that the data set already contains _annotations_, but no events.
To convert annotations to events, select `Tools -> Create events from annotations`.
The `Events` entry in the info panel now reads `90 (1, 2, 3)`, indicating there are a total of 90 events, with IDs 1, 2, and 3:
- 1 (annotation T0): rest onset
- 2 (annotation T1): onset of hand motor imagery
- 3 (annotation T2): onset of feet motor imagery

## Split into epochs
Go to `Tools -> Create Epochs...` (or select `Create epochs` in the toolbar).
In the dialog, select events `2` and `3` (the two task onsets).
You can click and drag to select multiple items in this dialog.
For `Interval around events:`, enter `-1.5` and `4.5` as start and end times, respectively.
Uncheck `Baseline Correction`, confirm with `OK`, and select `Create a new data set`.
In the info panel, the `Data type` of the newly created data set (`S001R06 (appended) (epoched)`) is now "Epochs".
If you select the original data set, you'll see that it is of type "Raw".
ERDS maps can only be calculated from "Epochs".

## Pick channels
Considering the motor imagery tasks, electrodes C3, Cz, and C4, should show the most activity.
Go to `Edit -> Pick channels...`, and select the required channels.
Don't worry about the channel names containing trailing dots.

## Plot ERDS maps
Select `Plot -> ERDS maps...` and enter the following configuration values:
- Frequency range: `2` to `36`
- Step size: `1`
- Time range: `-1` to `4`
- Baseline: `-1` to `0`

Check `Significance mask`, leave `alpha` at `0.05` and confirm with `OK`.
Calculating the significance masks can take about 30 seconds.
Two figures open up, one per event type.
