## [0.8.3] - 2022-04-21
### Fixed
- Fix XDF marker stream regression ([#346](https://github.com/cbrnr/mnelab/pull/346) by [Clemens Brunner](https://github.com/cbrnr))

## [0.8.2] - 2022-04-13
### Added
- Change the default cursor to a spinning wheel when the data is changed ([#341](https://github.com/cbrnr/mnelab/pull/341) by [Guillaume Favelier](https://github.com/GuillaumeFavelier))

### Fixed
- Fix XDF marker stream detection and loading ([#345](https://github.com/cbrnr/mnelab/pull/345) by [Clemens Brunner](https://github.com/cbrnr))

## [0.8.1] - 2022-03-29
### Fixed
- Fix loading of application icon ([#339](https://github.com/cbrnr/mnelab/pull/339) by [Guillaume Favelier](https://github.com/GuillaumeFavelier))

## [0.8.0] - 2022-03-25
### Added
- Add support to select and load multiple files at once ([#257](https://github.com/cbrnr/mnelab/pull/257) by [Florian Hofer](https://github.com/hofaflo))
- Add drag and drop reordering to sidebar ([#261](https://github.com/cbrnr/mnelab/pull/261) by [Florian Hofer](https://github.com/hofaflo))
- Add support for plotting evoked potentials averaged over channels (Plot -> Evoked comparison...) ([#256](https://github.com/cbrnr/mnelab/pull/256) by [Florian Hofer](https://github.com/hofaflo))
- Exceptions are now shown in an error message box instead of being silently caught ([#268](https://github.com/cbrnr/mnelab/pull/268) by [Florian Hofer](https://github.com/hofaflo))
- Add "Details" button to "Select XDF Stream" dialog ([#266](https://github.com/cbrnr/mnelab/pull/266) by [Florian Hofer](https://github.com/hofaflo))
- Add support for plotting evoked potentials for individual channels including topomaps (Plot -> Evoked...) ([#63](https://github.com/cbrnr/mnelab/pull/263) by [Florian Hofer](https://github.com/hofaflo))
- Add support for plotting topomaps of evoked potentials (Plot -> Evoked topomaps...) ([#277](https://github.com/cbrnr/mnelab/pull/277) by [Florian Hofer](https://github.com/hofaflo))
- Add montage name and location count to infowidget ([#271](https://github.com/cbrnr/mnelab/pull/271) by [Florian Hofer](https://github.com/hofaflo))
- Add possibility to specify `match_case`, `match_alias`, and `on_missing` to "Set montage..." ([#271](https://github.com/cbrnr/mnelab/pull/271) by [Florian Hofer](https://github.com/hofaflo))
- Add "Clear montage" to "Edit" menu ([#271](https://github.com/cbrnr/mnelab/pull/271) by [Florian Hofer](https://github.com/hofaflo))
- Add ability to pick channels by channel type ([#285](https://github.com/cbrnr/mnelab/pull/285) by [Florian Hofer](https://github.com/hofaflo))
- Add a settings menu (File -> Settings...) ([#289](https://github.com/cbrnr/mnelab/pull/289) by [Florian Hofer](https://github.com/hofaflo))
- Add ability to import events from FIF files ([#284](https://github.com/cbrnr/mnelab/pull/284) by [Florian Hofer](https://github.com/hofaflo))
- Add support for plotting ERDS topomaps (Plot -> ERDS topomaps...) ([#278](https://github.com/cbrnr/mnelab/pull/278) by [Florian Hofer](https://github.com/hofaflo))
- Add possibility to apply significance masks to ERDS plots ([#279](https://github.com/cbrnr/mnelab/pull/279) by [Florian Hofer](https://github.com/hofaflo))
- Add basic batch renaming of channels "Edit - Rename channels...") ([#303](https://github.com/cbrnr/mnelab/pull/303) by [Florian Hofer](https://github.com/hofaflo))
- Add support for loading data from .MAT files ([#314](https://github.com/cbrnr/mnelab/pull/314) by [Clemens Brunner](https://github.com/cbrnr))
- Add support for reading multiple XDF streams (via resampling) ([#312](https://github.com/cbrnr/mnelab/pull/312) by [Florian Hofer](https://github.com/hofaflo))
- Add app icon ([#319](https://github.com/cbrnr/mnelab/pull/319) by [Clemens Brunner](https://github.com/cbrnr))
- Add dialog to modify mapping between event IDs and labels (Edit - Events...) ([#302](https://github.com/cbrnr/mnelab/pull/302) by [Florian Hofer](https://github.com/hofaflo) and [Clemens Brunner](https://github.com/cbrnr))
- Add complete history for Find Events dialog ([#333](https://github.com/cbrnr/mnelab/pull/333) by [Clemens Brunner](https://github.com/cbrnr))

### Changed
- Simplify rereferencing workflow ([#258](https://github.com/cbrnr/mnelab/pull/258) by [Florian Hofer](https://github.com/hofaflo))
- Move "Show information..." from toolbar to "File" menu and rename to "Show XDF metadata" ([#266](https://github.com/cbrnr/mnelab/pull/266) by [Florian Hofer](https://github.com/hofaflo) and [#318](https://github.com/cbrnr/mnelab/pull/318) by [Clemens Brunner](https://github.com/cbrnr))
- Replace `utils.has_location` with `utils.count_locations`, which returns the number of locations instead of a boolean ([#271](https://github.com/cbrnr/mnelab/pull/271) by [Florian Hofer](https://github.com/hofaflo))
- Stop requiring existing annotations or events to enable editing them ([#283](https://github.com/cbrnr/mnelab/pull/283) by [Florian Hofer](https://github.com/hofaflo))
- Replace "(channels dropped)" suffix with "(channels picked)" and use `pick_channels` instead of `drop_channels` ([#285](https://github.com/cbrnr/mnelab/pull/285) by [Florian Hofer](https://github.com/hofaflo))
- The overwrite confirmation dialog is now fail-safe because it defaults to creating a new dataset ([#304](https://github.com/cbrnr/mnelab/pull/304) by [Clemens Brunner](https://github.com/cbrnr))
- Show signal length in hours, minutes, and seconds ([#334](https://github.com/cbrnr/mnelab/pull/334) by [Clemens Brunner](https://github.com/cbrnr))
- Show unique event counts if there are no more than seven unique event types in the main window ([#335](https://github.com/cbrnr/mnelab/pull/335) by [Clemens Brunner](https://github.com/cbrnr))

### Fixed
- Fix splitting name and extension for compatibility with Python 3.8 ([#252](https://github.com/cbrnr/mnelab/pull/252) by [Johan Medrano](https://github.com/yop0))
- Fix exporting to BrainVision with annotations starting with "BAD" or "EDGE" ([#276](https://github.com/cbrnr/mnelab/pull/276) by [Clemens Brunner](https://github.com/cbrnr))
- Exporting to .fif.gz now uses the correct extension on macOS ([#301](https://github.com/cbrnr/mnelab/pull/301) by [Clemens Brunner](https://github.com/cbrnr))
- Round physical minima and maxima to integers in EDF export ([#310](https://github.com/cbrnr/mnelab/pull/310) by [Clemens Brunner](https://github.com/cbrnr))
- Fix crop limit could exceed the signal length ([#336](https://github.com/cbrnr/mnelab/pull/336) by [Clemens Brunner](https://github.com/cbrnr))

## [0.7.0] - 2021-12-29
### Added
- Switch to [PySide6](https://www.qt.io/qt-for-python) ([#237](https://github.com/cbrnr/mnelab/pull/237) by [Clemens Brunner](https://github.com/cbrnr))
- Add button in Append dialog that simplifies moving data between source and destination lists ([#242](https://github.com/cbrnr/mnelab/pull/242) by [Clemens Brunner](https://github.com/cbrnr))
- Add dialog (File - Show XDF chunks...) which diplays chunk information for (possibly corrupted) XDF files ([#245](https://github.com/cbrnr/mnelab/pull/245) by [Clemens Brunner](https://github.com/cbrnr))

### Fixed
- Fix loading of XDF files that contained additional dots in their file names ([#244](https://github.com/cbrnr/mnelab/pull/244) and [#246](https://github.com/cbrnr/mnelab/pull/246) by [Clemens Brunner](https://github.com/cbrnr))
- Improve microvolts unit detection in XDF files ([#247](https://github.com/cbrnr/mnelab/pull/247) by [Clemens Brunner](https://github.com/cbrnr))

### Changed
- Remove requirements*.txt files ([#249](https://github.com/cbrnr/mnelab/pull/249) by [Clemens Brunner](https://github.com/cbrnr))

## [0.6.6] - 2021-11-19
### Added
- Add option to use effective sampling rate when importing XDF files ([#236](https://github.com/cbrnr/mnelab/pull/236) by [Clemens Brunner](https://github.com/cbrnr))
- Add option to disambiguate markers with identical names in different marker streams with the `prefix_markers` parameter ([#239](https://github.com/cbrnr/mnelab/pull/239) and [#240](https://github.com/cbrnr/mnelab/pull/240) by [Clemens Brunner](https://github.com/cbrnr))

### Fixed
- Fix history for importing XDF files and dropping channels ([#234](https://github.com/cbrnr/mnelab/pull/234) by [Clemens Brunner](https://github.com/cbrnr))

## [0.6.5] - 2021-11-08
### Fixed
- Fix EDF/BDF export of data containing stim channels ([#230](https://github.com/cbrnr/mnelab/pull/230) by [Clemens Brunner](https://github.com/cbrnr))
- Close EDF/BDF file in export ([#232](https://github.com/cbrnr/mnelab/pull/232) by [Clemens Brunner](https://github.com/cbrnr))

### Changed
- Remove support for Python 3.6 and 3.7 and add support for Python 3.10 ([#233](https://github.com/cbrnr/mnelab/pull/233) by [Clemens Brunner](https://github.com/cbrnr))

## [0.6.4] - 2021-10-19
### Fixed
- Remove auto-installation of `PySide2` when using `pip` ([#196](https://github.com/cbrnr/mnelab/pull/196) by [Clemens Brunner](https://github.com/cbrnr))
- Removing annotations and events is now as fast as it should be ([#206](https://github.com/cbrnr/mnelab/pull/206) and [#207](https://github.com/cbrnr/mnelab/pull/207) by [Clemens Brunner](https://github.com/cbrnr))
- Supported files can now be opened even if their extension is not all lower case (e.g. EDF) ([#212](https://github.com/cbrnr/mnelab/pull/212) by [Clemens Brunner](https://github.com/cbrnr))
- XDF files with missing channel units can now be imported ([#225](https://github.com/cbrnr/mnelab/pull/225) by [Clemens Brunner](https://github.com/cbrnr))
- Fix export to BrainVision files for newer versions of `pybv` ([#226](https://github.com/cbrnr/mnelab/pull/226) by [Clemens Brunner](https://github.com/cbrnr))
- XDF files containing channels in microvolts are now correctly scaled during import ([#227](https://github.com/cbrnr/mnelab/pull/227) by [Clemens Brunner](https://github.com/cbrnr))

### Changed
- Rename `master` branch to `main` ([#193](https://github.com/cbrnr/mnelab/pull/193) by [Clemens Brunner](https://github.com/cbrnr))
- Simplify dependencies ([#199](https://github.com/cbrnr/mnelab/pull/199) by [Clemens Brunner](https://github.com/cbrnr))
- Switch to `setup.cfg` ([#216](https://github.com/cbrnr/mnelab/pull/216) by [Clemens Brunner](https://github.com/cbrnr))
- Remove instructions and workarounds specific to `conda` environments ([#223](https://github.com/cbrnr/mnelab/pull/223) by [Clemens Brunner](https://github.com/cbrnr))

## [0.6.3] - 2021-01-05
### Added
- Add Python 3.9 support ([#190](https://github.com/cbrnr/mnelab/pull/190) by [Clemens Brunner](https://github.com/cbrnr))

### Fixed
- Fix export functionality ([#184](https://github.com/cbrnr/mnelab/pull/184) by [Guillaume Dollé](https://github.com/gdolle))
- Fix ICA computation in separate process ([#192](https://github.com/cbrnr/mnelab/pull/192) by [Clemens Brunner](https://github.com/cbrnr))

### Changed
- PySide2 installed by default if wrapped Qt bindings (PyQt5, PySide2) are not found ([#187](https://github.com/cbrnr/mnelab/pull/187) by [Guillaume Dollé](https://github.com/gdolle))

## [0.6.2] - 2020-10-30
### Fixed
- Include `requirements-extras.txt` in MANIFEST.in (by [Clemens Brunner](https://github.com/cbrnr))

## [0.6.1] - 2020-10-30
### Fixed
- Include `requirements.txt` in MANIFEST.in (by [Clemens Brunner](https://github.com/cbrnr))

## [0.6.0] - 2020-10-30
### Added
- Add option to convert events to annotations ([#166](https://github.com/cbrnr/mnelab/pull/166) by [Alberto Barradas](https://github.com/abcsds))
- Retain annotation descriptions when converting to events ([#170](https://github.com/cbrnr/mnelab/pull/170) by [Alberto Barradas](https://github.com/abcsds) and [Clemens Brunner](https://github.com/cbrnr))
- Add support for basic ERDS maps ([#174](https://github.com/cbrnr/mnelab/pull/174) by [Clemens Brunner](https://github.com/cbrnr))
- Add syntax highlighting in history dialog ([#179](https://github.com/cbrnr/mnelab/pull/179) by [Clemens Brunner](https://github.com/cbrnr))
- Add copy to clipboard in history dialog ([#180](https://github.com/cbrnr/mnelab/pull/180) by [Clemens Brunner](https://github.com/cbrnr))

### Fixed
- Show correct signal length in seconds ([#168](https://github.com/cbrnr/mnelab/pull/168) by [Clemens Brunner](https://github.com/cbrnr))
- Fix export functionality ([#177](https://github.com/cbrnr/mnelab/pull/177) by [Guillaume Dollé](https://github.com/gdolle) and [Clemens Brunner](https://github.com/cbrnr))

### Changed
- Required dependencies are now listed only in one place (requirements.txt) ([#172](https://github.com/cbrnr/mnelab/pull/172) by [Clemens Brunner](https://github.com/cbrnr))

## [0.5.7] - 2020-07-13
### Fixed
- Include missing icons in package ([#158](https://github.com/cbrnr/mnelab/pull/158) by [Clemens Brunner](https://github.com/cbrnr))

## [0.5.6] - 2020-06-12
### Added
- Add support for automatic light/dark mode switching on macOS ([#152](https://github.com/cbrnr/mnelab/pull/152) by [Clemens Brunner](https://github.com/cbrnr))

### Fixed
- Fix bug that prevented exporting data ([#156](https://github.com/cbrnr/mnelab/pull/156) by [Clemens Brunner](https://github.com/cbrnr))

## [0.5.5] - 2020-06-03
### Added
- Add support for appending continuous raw data ([#108](https://github.com/cbrnr/mnelab/pull/108) by [Lukas Stranger](https://github.com/stralu) and [Clemens Brunner](https://github.com/cbrnr))
- Add support for appending epoched data ([#135](https://github.com/cbrnr/mnelab/pull/135) by [Lukas Stranger](https://github.com/stralu))
- Add support for NIRS data and conversion to optical density and haemoglobin ([#145](https://github.com/cbrnr/mnelab/pull/145) by [Robert Luke](https://github.com/rob-luke) and [Clemens Brunner](https://github.com/cbrnr))

### Fixed
- Fix loading of BrainVision files that have an extension other than .eeg ([#142](https://github.com/cbrnr/mnelab/pull/142) by [Clemens Brunner](https://github.com/cbrnr))

### Changed
- Use [QtPy](https://github.com/spyder-ide/qtpy) to support both PyQt5 and PySide2 ([#118](https://github.com/cbrnr/mnelab/pull/118) by [Clemens Brunner](https://github.com/cbrnr))
- Remove resource file and include icons directly ([#125](https://github.com/cbrnr/mnelab/pull/125) by [Clemens Brunner](https://github.com/cbrnr))
- Improve internal logic of the ICA dialog ([#136](https://github.com/cbrnr/mnelab/pull/136) by [Lukas Stranger](https://github.com/stralu) and [Clemens Brunner](https://github.com/cbrnr))
- Remove Pebble again and use `multiprocessing.Pool` ([#140](https://github.com/cbrnr/mnelab/pull/140) by [Clemens Brunner](https://github.com/cbrnr))
- Require MNE >= 0.20 ([#146](https://github.com/cbrnr/mnelab/pull/146) by [Clemens Brunner](https://github.com/cbrnr))
- Add function `utils.has_locations` to determine if channel locations are available ([#147](https://github.com/cbrnr/mnelab/pull/147) by [Clemens Brunner](https://github.com/cbrnr))
- Refactor readers and writers ([#148](https://github.com/cbrnr/mnelab/pull/148) by [Clemens Brunner](https://github.com/cbrnr))

## [0.5.3] - 2020-02-03
### Added
- Add history for setting reference ([#100](https://github.com/cbrnr/mnelab/pull/100) by [Clemens Brunner](https://github.com/cbrnr))
- Add history for setting montage, switching/duplicating data sets, plot PSD, and plotting data with events ([#109](https://github.com/cbrnr/mnelab/pull/109) by [Clemens Brunner](https://github.com/cbrnr))

### Fixed
- Fix blurry icons on macOS HiDPI screens ([#102](https://github.com/cbrnr/mnelab/pull/102) by [Clemens Brunner](https://github.com/cbrnr))
- Use `mne.channels.make_standard_montage` instead of deprecated `mne.channels.read_montage` ([#107](https://github.com/cbrnr/mnelab/pull/107) by [Clemens Brunner](https://github.com/cbrnr))
- Ensure MNELAB is run using a "framework build" of Python on `conda` installations on macOS ([#119](https://github.com/cbrnr/mnelab/pull/119) by [Richard Höchenberger](https://github.com/hoechenberger))

### Changed
- Use environment markers in `setup.py` for `install_requires` ([#105](https://github.com/cbrnr/mnelab/pull/105) by [Clemens Brunner](https://github.com/cbrnr))
- Bump required minimum MNE version to 0.19 ([#107](https://github.com/cbrnr/mnelab/pull/107) by [Clemens Brunner](https://github.com/cbrnr))
- Spawn ICA process pool via `Pebble` instead of `multiprocessing` to avoid Python segfaulting on macOS `conda` installations ([#119](https://github.com/cbrnr/mnelab/pull/119) by [Richard Höchenberger](https://github.com/hoechenberger))

## [0.5.2] - 2019-10-30
### Fixed
- Fix multiprocessing runtime error (context has already been set) ([#98](https://github.com/cbrnr/mnelab/pull/98) by [Clemens Brunner](https://github.com/cbrnr))

## [0.5.1] - 2019-10-24
### Fixed
- Remove binary wheel on PyPI because of a macOS-only package dependency ([#95](https://github.com/cbrnr/mnelab/pull/95) by [Clemens Brunner](https://github.com/cbrnr))

## [0.5.0] - 2019-10-23
### Added
- MNELAB is now shown as an app name in the menu bar on macOS ([#83](https://github.com/cbrnr/mnelab/pull/83) by [Clemens Brunner](https://github.com/cbrnr))
- The About dialog now lists all package dependencies ([#88](https://github.com/cbrnr/mnelab/pull/88) by [Clemens Brunner](https://github.com/cbrnr))
- Added a dialog (File - Show Information) that shows XDF meta information (stream headers and footers) ([#92](https://github.com/cbrnr/mnelab/pull/92) by [Clemens Brunner](https://github.com/cbrnr))

### Fixed
- Fixed dropping XDF files on MNELAB and loading XDF files without channel labels ([#86](https://github.com/cbrnr/mnelab/pull/86) by [Clemens Brunner](https://github.com/cbrnr))
- Disable XDF streams of type string in selection dialog ([#90](https://github.com/cbrnr/mnelab/pull/90) by [Clemens Brunner](https://github.com/cbrnr))

## [0.4.0] - 2019-09-04
### Added
- Add MNELAB logo to About dialog (by [Clemens Brunner](https://github.com/cbrnr))
- Export data is split into submenus with a separate entry for each supported export format ([#66](https://github.com/cbrnr/mnelab/pull/66) by [Clemens Brunner](https://github.com/cbrnr))
- Add support for exporting to BrainVision files ([#68](https://github.com/cbrnr/mnelab/pull/68) and [#75](https://github.com/cbrnr/mnelab/pull/75) by [Clemens Brunner](https://github.com/cbrnr))
- Add support for loading .fif.gz files ([#74](https://github.com/cbrnr/mnelab/pull/74) by [Clemens Brunner](https://github.com/cbrnr))
- Add support for loading Neuroscan .cnt, EGI Netstation .mff, and Nexstim eXimia .nxe file formats ([#77](https://github.com/cbrnr/mnelab/pull/77) by [Clemens Brunner](https://github.com/cbrnr))
- Add support for cropping data ([#78](https://github.com/cbrnr/mnelab/pull/78) by [Clemens Brunner](https://github.com/cbrnr))

### Fixed
- Correctly report file size for BrainVision data ([#69](https://github.com/cbrnr/mnelab/pull/69) by [Clemens Brunner](https://github.com/cbrnr))
- Retain events when creating epochs ([#73](https://github.com/cbrnr/mnelab/pull/73) by [Clemens Brunner](https://github.com/cbrnr))
- Better handling of file extensions (especially when there are multiple extensions such as .fif.gz) ([#74](https://github.com/cbrnr/mnelab/pull/74) by [Clemens Brunner](https://github.com/cbrnr))

### Changed
- The internally used ``have`` dictionary now contains version numbers for existing modules ([#76](https://github.com/cbrnr/mnelab/pull/76) by [Clemens Brunner](https://github.com/cbrnr))

## [0.3.0] - 2019-08-13
### Added
- Add option to interpolate bad channels ([#55](https://github.com/cbrnr/mnelab/pull/55) by [Victor Férat](https://github.com/vferat))
- Add dialog to show the command history ([#58](https://github.com/cbrnr/mnelab/pull/58) by [Clemens Brunner](https://github.com/cbrnr))
- Add history when changing channel properties (e.g. bads, channel names, channel types) ([#59](https://github.com/cbrnr/mnelab/pull/59) by [Clemens Brunner](https://github.com/cbrnr))
- Add toolbar ([#61](https://github.com/cbrnr/mnelab/pull/61) by [Clemens Brunner](https://github.com/cbrnr))

### Fixed
- Update view when all bads have been deselected in channel properties dialog (by [Clemens Brunner](https://github.com/cbrnr))
- Fix visual glitch in info widget when showing error dialogs ([#57](https://github.com/cbrnr/mnelab/pull/57) by [Clemens Brunner](https://github.com/cbrnr))

## [0.2.0] - 2019-07-11
### Added
- Show version number in About dialog ([#28](https://github.com/cbrnr/mnelab/pull/28) by [Clemens Brunner](https://github.com/cbrnr))
- Add "Apply ICA" to Tools menu that allows users to apply a fitted ICA solution to the current dataset ([#43](https://github.com/cbrnr/mnelab/pull/43) by [Victor Férat](https://github.com/vferat))
- Plot raw shows the dataset name in the title (instead of "Raw data") (by [Clemens Brunner](https://github.com/cbrnr))
- Add option to convert annotations to events ([#50](https://github.com/cbrnr/mnelab/pull/50) by [Clemens Brunner](https://github.com/cbrnr))
- Enable epoching of continuous data ([#45](https://github.com/cbrnr/mnelab/pull/45) by [Tanguy Vivier](https://github.com/TyWR) and [Clemens Brunner](https://github.com/cbrnr))

### Fixed
- Fix crash when no channel labels are present in XDF file (by [Clemens Brunner](https://github.com/cbrnr))
- Fix crash when opening a file from the Recent menu that doesn't exist anymore ([#37](https://github.com/cbrnr/mnelab/pull/37) by [Clemens Brunner](https://github.com/cbrnr))
- Fix crash when opening a BrainVision VHDR file where the EEG and/or VMRK file(s) are missing ([#46](https://github.com/cbrnr/mnelab/pull/46) by [Clemens Brunner](https://github.com/cbrnr))
- Fix crash when dropping channels (when using MNE < 0.19) ([#49](https://github.com/cbrnr/mnelab/pull/49) by [Clemens Brunner](https://github.com/cbrnr))
- Fix crash when importing annotations ([#54](https://github.com/cbrnr/mnelab/pull/54) by [Clemens Brunner](https://github.com/cbrnr))

## [0.1.0] - 2019-06-27
### Added
- Initial release (by [Clemens Brunner](https://github.com/cbrnr))
