# Changelog

## [2.0.0] - 2024-09-05

### Changed

- **Breaking:** migrated to dcm-common (version 3) (`66b8514d`)

## [1.0.0] - 2024-04-04

### Changed

- **Breaking:** switched to new implementation of `lzvnrw_supplements.Logger` and renamed `report`-property to `log` (`adf04930`, `de3262c0`)
- **Breaking:** simplified naming scheme for file_format-plugins (`8bf28c67`)
- improved test-suites for jhove- and bagit_profile-modules (`8bf28c67`)

### Added

- added DEFAULT_FILE_FORMATS property to file_format-plugins (`b40d2e43`)
- added py.typed marker to package (`10d50719`)

### Fixed

- fixed issue with third-party modules and JSON response format in jhove-plugin (`783c1b0e`)
- fixed issue where text/plain files caused a crash in jhove-plugin (`afec8d70`)

## [0.4.0] - 2023-12-18

### Added
- `file_format`: added file-format validation for individual files (`144c5627`)

## [0.3.5] - 2023-12-13

### Changed
- isolated file format (MIME-type) identification using fido from the`file_format`'s-bag validation method (`c429f04d`)

### Added 
- add validator self-descriptions in the form of `VALIDATOR_SUMMARY` and `VALIDATOR_DESCRIPTION` (`b8eae5a8`)


## [0.3.3] - 2023-11-23

### Fixed
- unpin lzvnrw-dependencies (`6193fffc`)
- fixed missing remote profile with local file fixture (`068b4b4e`)
- fixed conditional build/push pipeline (`714aa63a`)


## [0.3.0] - 2023-10-20

### Changed

- initial release of the validator library
