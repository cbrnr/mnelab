# Pipelines

A pipeline repeats recorded processing steps on another dataset. Each dataset in the sidebar inherits its parent's steps, so a pipeline can start at any point in the dataset tree.

1. Process a dataset, then right-click it in the sidebar and select **Create Pipeline from Here**. The same action is available under **Process → Create Pipeline from Dataset**.
2. In the editor, reorder or remove steps as needed. Steps marked with a warning cannot be replayed and must be removed. Click **OK**.
3. Select a target dataset and choose **Process → Apply Pipeline**. The result appears as a new dataset; the target stays unchanged.

**Process → Pipeline...** opens the editor at any time. **Save...** and **Load...** store and retrieve pipelines as JSON files.

Supported steps include filtering, line noise removal, resampling, cropping, channel and reference changes, bad-channel interpolation, montage changes, events and annotations, and epoch creation or rejection. File imports and **Apply ICA** can also be replayed. **Run ICA** cannot be replayed yet.

For file imports, MNELAB suggests a matching rule when the import and original dataset files share a folder and name prefix. Importing `s01-bad_channels.csv` into `s01.fif`, for example, makes the pipeline look for `s02-bad_channels.csv` when applied to `s02.fif`. Matching also works on derived datasets because their original filenames are retained.

Without a matching filename, imported bad channels, events, and annotations are stored in the pipeline JSON. **File Rule...** switches between embedded contents and matching files. Embedded annotations retain their time units; sample-based annotations use the target's sampling frequency. ICA solutions require either a matching file or a fixed file path.

Built-in montages are loaded by name, while custom coordinates are stored in the pipeline. **File Rule...** can instead select a matching montage file. A step using an embedded montage requires one in the target dataset.

If a file is missing or a step is incompatible, MNELAB reports the failed step and leaves the target unchanged.
