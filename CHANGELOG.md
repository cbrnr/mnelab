## [0.2.0] - 2019-07-11
### Added
- Show version number in About dialog ([#28](https://github.com/cbrnr/mnelab/pull/28) by [Clemens Brunner](https://github.com/cbrnr))
- Add "Apply ICA" to Tools menu that allows users to apply a fitted ICA solution to the current dataset ([#43](https://github.com/cbrnr/mnelab/pull/43) by [Victor Férat](https://github.com/vferat))
- Plot raw shows the dataset name in the title (instead of "Raw data") (by [Clemens Brunner](https://github.com/cbrnr))
- Add option to convert annotations to events ([#50](https://github.com/cbrnr/mnelab/pull/50) by [Clemens Brunner](https://github.com/cbrnr))
- Enable epoching of continuous data ([#45](https://github.com/cbrnr/mnelab/pull/45) by [Tanguy Vivier](https://github.com/TyWR) and [Clemens Brunner](https://github.com/cbrnr))
- Add option to interpolate bad channels ([#55](https://github.com/cbrnr/mnelab/pull/55) by [Victor Férat](https://github.com/vferat))

### Fixed
- Fix crash when no channel labels are present in XDF file (by [Clemens Brunner](https://github.com/cbrnr))
- Fix crash when opening a file from the Recent menu that doesn't exist anymore ([#37](https://github.com/cbrnr/mnelab/pull/37) by [Clemens Brunner](https://github.com/cbrnr))
- Fix crash when opening a BrainVision VHDR file where the EEG and/or VMRK file(s) are missing ([#46](https://github.com/cbrnr/mnelab/pull/46) by [Clemens Brunner](https://github.com/cbrnr))
- Fix crash when dropping channels (when using MNE < 0.19) ([#49](https://github.com/cbrnr/mnelab/pull/49) by [Clemens Brunner](https://github.com/cbrnr))
- Fix crash when importing annotations ([#54](https://github.com/cbrnr/mnelab/pull/54) by [Clemens Brunner](https://github.com/cbrnr))

## [0.1.0] - 2019-06-27
### Added
- Initial release (by [Clemens Brunner](https://github.com/cbrnr))
