# Pipelines

A pipeline repeats recorded processing steps on another dataset. Each dataset in the sidebar inherits its parent's steps, so a pipeline can start at any point in the dataset tree.

1. Process a dataset, then right-click it in the sidebar and select *Create Pipeline from Here*. The same action is available under *Process – Create Pipeline from Dataset*.
2. In the dialog window, reorder or remove steps as needed. Steps marked with a warning cannot be replayed and must be removed before the pipeline can be applied or saved. Click *OK*.
3. Select a target dataset and choose *Process – Apply Pipeline*. The result appears as a new dataset; the target stays unchanged as its parent.

*Process – Pipeline…* opens the pipeline editor at any time. *Save…* and *Load…* store and retrieve pipelines as JSON files.

Supported steps include filtering, line noise removal, resampling, cropping, channel and reference changes, bad-channel interpolation, montage changes, events and annotations, and epoch creation or rejection. File imports and *Apply ICA* can also be replayed.

For file imports, MNELAB can find a separate file for each target dataset. If the imported file and the dataset's original file are in the same folder and share a name prefix, MNELAB suggests a rule using `{id}` for that shared part. For example, importing `s01-bad_channels.csv` into `s01.fif` produces the dataset pattern `{id}.fif` and matching-file pattern `{id}-bad_channels.csv`. Applying the pipeline to `s02.fif` then reads `s02-bad_channels.csv` from the same folder. This also works on processed or duplicated datasets because MNELAB retains their original filenames.

Without a matching filename, MNELAB stores imported bad channels, events, or annotations in the pipeline JSON, so the original import file is no longer needed. To change this, select the import step and click *File Rule…* to choose *Matching file for each dataset* or *Embed contents in pipeline*. For a matching rule, the dialog previews the file path for the selected dataset. Embedded annotations retain their original time units; annotations measured in samples use the target dataset's sampling frequency. ICA solutions cannot be embedded and must use either a matching file or one fixed file path.

Montage steps can set or clear channel locations. Built-in montages are saved by name and loaded from MNE when the pipeline runs. Coordinates from a custom montage file are saved in the pipeline, so replay does not require the original file. For a different montage file per dataset, select the montage step and use *File Rule…* to set up a matching file. A step labeled *Use Target's Embedded Montage* requires the target dataset to contain an embedded montage.

If a file is missing or a step is incompatible, MNELAB reports the failed step and leaves the target unchanged.
