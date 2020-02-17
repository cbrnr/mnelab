## [Unreleased] - XXXX-XX-XX
### Added
- Add support for appending continuous raw data ([#108](https://github.com/cbrnr/mnelab/pull/108) by [Lukas Stranger](https://github.com/stralu) and [Clemens Brunner](https://github.com/cbrnr))
- Add support for appending epoched data ([#135](https://github.com/cbrnr/mnelab/pull/135) by [Lukas Stranger](https://github.com/stralu) and [Clemens Brunner](https://github.com/cbrnr))

### Changed
- Use [QtPy](https://github.com/spyder-ide/qtpy) to support both PyQt5 and PySide2 ([#118](https://github.com/cbrnr/mnelab/pull/118) by [Clemens Brunner](https://github.com/cbrnr))
- Remove resource file and include icons directly ([#125](https://github.com/cbrnr/mnelab/pull/125) by [Clemens Brunner](https://github.com/cbrnr)) 

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
