# Pipelines

A pipeline repeats the processing steps used to make a dataset. MNELAB records replayable steps as you use its normal menus, and each child in the sidebar inherits the steps of its parent.

1. Process a dataset with the usual MNELAB actions.
2. Right-click a dataset with recorded steps in the sidebar and choose **Create Pipeline from Here**. The pipeline contains the steps leading to that point in the dataset tree. You can also select the dataset and choose **Process → Create Pipeline from Dataset**.
3. Review the steps. Use **Move Up**, **Move Down**, **Remove**, or **Clear** to change the sequence.
4. Select a target dataset and choose **Process → Apply Pipeline**. MNELAB creates a new dataset with the result; the target stays available in the sidebar.

Supported steps include filtering, line noise removal, resampling, cropping, channel selection and properties, changing reference, bad-channel interpolation, finding or converting events and annotations, creating epochs, and dropping bad epochs. Imported bad channels, events, annotations, and ICA solutions can also be replayed. An imported ICA solution can be followed by **Apply ICA**. **Run ICA** remains a normal processing action but cannot be replayed by a pipeline yet. Operations that cannot be replayed appear with a warning in the pipeline editor. Remove those steps before saving or applying the pipeline.

File imports can use a matching file for each target dataset. When the imported file and the dataset's original file are in the same directory and share a name prefix, MNELAB suggests a matching rule. For example, importing `s01-bad_channels.csv` into `s01.fif` records dataset filename `{id}.fif` and matching file `{id}-bad_channels.csv`. Applying the pipeline to `s02.fif` then reads `s02-bad_channels.csv` from the target file's directory. The original dataset filename is retained when a dataset is duplicated or processed, so matching also works on derived datasets.

For imported bad channels, events, and annotations without a matching filename, MNELAB stores the imported contents in the pipeline JSON. You can switch between **Matching file for each dataset** and **Embed contents in pipeline** with **File Rule...**. Embedded annotations keep their original time units, so annotations measured in samples use the target dataset's sampling frequency. ICA solutions remain file-based: choose either a matching file or a fixed file path. A missing or incompatible file stops the pipeline and leaves the target unchanged.

Setting or clearing a montage can also be replayed. Built-in montages are stored by name and loaded from MNE when the pipeline runs. Custom montage coordinates are saved in the pipeline by default, so the original montage file is not needed for replay. For a subject-specific montage file, select its step and use **File Rule...** to choose a matching file instead. A step that uses the target's embedded montage requires the target dataset to have one.

Use **Process → Pipeline...** to review the current pipeline or load one without processing a dataset first. **Save...** stores it as a JSON file for later use. If a step is incompatible with the target data, MNELAB reports which step failed and leaves the target dataset unchanged.
