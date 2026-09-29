# Pipelines

A pipeline repeats the processing steps used to make a dataset. MNELAB records replayable steps as you use its normal menus, and each child in the sidebar inherits the steps of its parent.

1. Process a dataset with the usual MNELAB actions.
2. Right-click a dataset with recorded steps in the sidebar and choose **Create Pipeline from Here**. The pipeline contains the steps leading to that point in the dataset tree. You can also select the dataset and choose **Process → Create Pipeline from Dataset**.
3. Review the steps. Use **Move Up**, **Move Down**, **Remove**, or **Clear** to change the sequence.
4. Select a target dataset and choose **Process → Apply Pipeline**. MNELAB creates a new dataset with the result; the target stays available in the sidebar.

Supported steps include filtering, line noise removal, resampling, cropping, channel selection and properties, changing reference, bad-channel interpolation, finding or converting events and annotations, creating epochs, and dropping bad epochs. Operations that cannot be replayed appear with a warning in the pipeline editor. Remove those steps before saving or applying the pipeline.

Setting or clearing a montage can also be replayed. Built-in montages are stored by name and loaded from MNE when the pipeline runs. Custom montage coordinates are saved in the pipeline, so the original montage file is not needed for replay. An embedded montage step uses the montage embedded in the target dataset and requires the target to have one.

Use **Process → Pipeline...** to review the current pipeline or load one without processing a dataset first. **Save...** stores it as a JSON file for later use. If a step is incompatible with the target data, MNELAB reports which step failed and leaves the target dataset unchanged.
