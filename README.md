# LZV.nrw DCM Bag Validator
This package is derived from the `bagit_profile`-package.

## Setup
Install this package and its (required) dependencies by issuing `pip install .` or to include changes continuously `pip install -e .`.

## Package-Structure
The package `dcm_bag_validator` contains a set of different validation modules for the validation of `BagIt`-Bags against some specification.
In the context of the LZV.nrw-project, this specification is represented by a `BagIt`(-metadata)-profile as well as a payload directory structure-profile (payload-profile for short).
Furthermore, a validation of Bag manifests is included.

The package has the following structure:
```
dcm-bag-validator/
  ├── dcm_bag_validator/
  │   ├── file_format_plugins/   # plugins for FileFormatValidator
  │   │   │                      # as defined in file_format.py
  │   │   ├── file_format_interface.py   # plugin interface-definition
  │   │   ├── jhove.py           # plugin for validation based on jhove
  │   │   └── example.py         # example-plugin (naive validation based
  │   │                          # on file extension)
  │   ├── validator.py           # wrapper, concisely utilize all
  │   │                          # validator modules
  │   ├── bagit_profile.py       # validate against bagit-profile
  │   ├── payload_structure.py   # validate against payload-profile
  │   ├── payload_integrity.py   # validate integrity of payload
  │   ├── file_format.py         # validate file format
  │   ├── file_integrity.py      # file integrity (checksum)
  │   └── errors.py              # definition of module-specific
  │                              # error classes
  ├── test_dcm_bag_validator/    # testing suite for the dcm_bag_validator-
  │   │                          # package; validator components are
  │   │                          # tested individually in their respective
  │   │                          # modules in corresponding sub-directories
  │   ├── fixtures/              # common fixtures for automated tests
  │   ├── test_<X>
  │   └── ...
  ├── README.md
  └── ...
```
Alternatively, the package structure can be described by the following block diagram:
```
                 │    Sub-Modules               │
                 │    └ Validator Components    +  File Format
                 │ (defining validator classes) │  Validator-Plugins
                     ┌─────────────────────┐
                 ┌───┤bagit_profile.py     │
                 │   └─────────────────────┘
                 │
                 │   ┌─────────────────────┐
┌─────────────┐  ├───┤payload_structure.py │
│ dcm-        │  │   └─────────────────────┘
│ bag-        ├──┤                               ┌──────────────────────┐
│ validator   │  │   ┌─────────────────────┐  ┌──┤file_format_interface │
└─────────────┘  ├───┤payload_integrity.py │  │  ├──────────────────────┤
                 │   └─────────────────────┘  │  │* example.py          │
                 │                            │  │                      │
                 │   ┌─────────────────────┐  │  │* jhove.py            │
                 ├───┤file_format.py       ├──┘  │                      │
                 │   └─────────────────────┘     │* ...                 │
                 │                               └──────────────────────┘
                 │   ┌─────────────────────┐
                 ├───┤file_integrity.py    │
                 │   └─────────────────────┘
                 │   ┌─────────────────────┐
                 └───┤...                  │
                     └─────────────────────┘
```

## Requirements
 * All python-dependencies for the use of this library are listed in `requirements.txt`.
 * Jhove integration in the file-format-validation additionally requires a suitable java installation and setup (i.e. the java-binary needs to be available from the system path variable). Furthermore, the jhove-starter has to be defined either also via the path variable or via environment variable `JHOVE_APP` (jhove config can be provided analogously by using `JHOVE_APP_CONF`). You can use the following set of commands to setup a `java`-installation in the directory `jdk` of the current working dir:
   ```
   mkdir venv &&
   python3 -m venv venv &&
   source venv/bin/activate &&
   pip install install-jdk &&
   mkdir jdk &&
   python3 -c "import jdk; jdk.install('17', vendor='Corretto', path='jdk')" &&
   javapath=$(python3 -c "import glob; dirlist = glob.glob('jdk/**/bin/java'); print(glob.glob('jdk/**/bin/java')[0] if isinstance(dirlist, list) else 'No java binary found')") &&
   deactivate &&
   rm -rf venv &&
   $(realpath $javapath) -version &&
   echo "binary is located at: $(realpath $javapath)"
   ```
   Update the path variable (of the active shell) for the jhove-installation
   ```
   export PATH=$(dirname $javapath):${PATH}
   ```
   The `jhove`-application can then be installed for example by using:
   ```
   wget -q "http://software.openpreservation.org/rel/jhove-latest.jar" &&
   echo '<?xml version="1.0" encoding="UTF-8" standalone="no"?><AutomatedInstallation langpack="eng"><com.izforge.izpack.panels.htmlinfo.HTMLInfoPanel id="welcome"/><com.izforge.izpack.panels.target.TargetPanel id="install_dir"><installpath>'$(realpath jhove)'</installpath></com.izforge.izpack.panels.target.TargetPanel><com.izforge.izpack.panels.packs.PacksPanel id="sdk_pack_select"><pack index="0" name="JHOVE Application" selected="true"/><pack index="1" name="JHOVE Shell Scripts" selected="true"/><pack index="2" name="JHOVE External Modules" selected="true"/></com.izforge.izpack.panels.packs.PacksPanel><com.izforge.izpack.panels.install.InstallPanel id="install"/><com.izforge.izpack.panels.finish.FinishPanel id="finish"/></AutomatedInstallation>' > jhove-auto-install.xml &&
   java -jar jhove-latest.jar jhove-auto-install.xml &&
   rm jhove-auto-install.xml jhove-latest.jar &&
   jhove/jhove
   echo "binary is located at: $(realpath jhove/jhove)"
   ```

## Test
Install test-related dependencies with `pip install -r dev-requirements.txt`.
This repository contains multiple test-settings organized in separate modules:
 * a BagIt-profile-related test-module `test_validator_profile.py`

   *testing interaction with third-party libraries and custom additions in the context of LZV.nrw*

   and
 * a test module `test_payload_structure.py`

   *that is concerned with the dcm-specific payload structure requirements to a Bag; a more selective set of tests for the validation of the payload structure based on a minimal payload-profile*
 * a test module `test_payload_integrity.py`

   *that focuses on the general payload integrity requirements to a Bag; a small set of tests for the validation of the payload integrity based on the `bagit`-library*
 * a test module `test_file_format.py`

   *that focuses on the basic validation functionality based on the `file_format.py`-module and the plugin-interface*
 * a test module `test_jhove.py`

   *which provides tests and examples for the use of the jhove-plugin for file-format validation*
 * a test module `test_file_integrity.py`

   *that tests the basic functionality of the `file_integrity.py` module*

Run `pytest`-Tests with `pytest -v -s`.

# Contributors
* Sven Haubold
* Orestis Kazasidis
* Stephan Lenartz
* Kayhan Ogan
* Michael Rahier
* Steffen Richters-Finger
* Malte Windrath
