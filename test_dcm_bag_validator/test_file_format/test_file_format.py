"""
This module contains pytest-tests for testing the features of the
validator itself.

All tests use copies of the test-bag located in EXAMPLE_BAG_FIXTURE_PATH
(copied to EXAMPLE_BAG_WORKING_PATH).
"""

import shutil
from pathlib import Path

import pytest
from dcm_common import LoggingContext as Context

from dcm_bag_validator import errors, file_format
from dcm_bag_validator.file_format_plugins import example


EXAMPLE_BAG_FIXTURE_PATH = Path("test_dcm_bag_validator/fixtures/example_bag")
EXAMPLE_BAG_WORKING_PATH = Path("tmp/example_bag_copy")


def duplicate_example_bag():
    """Duplicate the example bag in fixtures to (cleaned) working dir."""

    if EXAMPLE_BAG_WORKING_PATH.is_dir():
        shutil.rmtree(EXAMPLE_BAG_WORKING_PATH)
    shutil.copytree(EXAMPLE_BAG_FIXTURE_PATH, EXAMPLE_BAG_WORKING_PATH)


@pytest.fixture(scope="session", autouse=True)
def cleanup(request):
    """Cleanup a testing directory once we are finished."""

    def remove_test_dir():
        if EXAMPLE_BAG_WORKING_PATH.is_dir():
            shutil.rmtree(EXAMPLE_BAG_WORKING_PATH)
        if EXAMPLE_BAG_WORKING_PATH.parent.is_dir():
            EXAMPLE_BAG_WORKING_PATH.parent.rmdir()
    request.addfinalizer(remove_test_dir)


# test type selector for file format given in plugin default
def test_example_plugin_valid_file_format_types_from_default():
    # load profile into validator
    some_validator = file_format.FileFormatValidator(
        [(example.ExamplePlugin.DEFAULT_FILE_FORMATS, example.ExamplePlugin())]
    )
    # and make a copy of a valid example bag
    duplicate_example_bag()

    # test bag format
    assert some_validator.validate_bag(
        str(EXAMPLE_BAG_WORKING_PATH)
    ) == 0


# test type selector for file format as list of MIME-types
def test_example_plugin_valid_file_format_types_as_list():
    # load profile into validator
    some_validator = file_format.FileFormatValidator(
        [(["text/plain"], example.ExamplePlugin())]
    )
    # and make a copy of a valid example bag
    duplicate_example_bag()

    # test bag format
    assert some_validator.validate_bag(
        str(EXAMPLE_BAG_WORKING_PATH)
    ) == 0

# test type selector for file format as regex for MIME-types
def test_example_plugin_valid_file_format_types_as_regex():
    # load profile into validator
    some_validator = file_format.FileFormatValidator(
        [(r"image/.*", example.ExamplePlugin())]
    )
    # and make a copy of a valid example bag
    duplicate_example_bag()

    # test bag format
    assert some_validator.validate_bag(
        str(EXAMPLE_BAG_WORKING_PATH)
    ) == 0

# repeat test_example_plugin_valid_file_format_types_as_regex() but
# provoke FileFormatValidationError by changing a file extension
def test_example_plugin_invalid_file_format_types_as_regex(
    pattern_in_list_of_strings
):
    # load profile into validator
    some_validator = file_format.FileFormatValidator(
        [(r"image/.*", example.ExamplePlugin())]
    )
    # and make a copy of a valid example bag
    duplicate_example_bag()

    # change payload file extension
    bag_payload_file = \
        EXAMPLE_BAG_WORKING_PATH \
            / "data" \
            / "preservation_master" \
            / "sample.png"
    bag_payload_file.rename(bag_payload_file.with_suffix(".jpg"))

    # test bag format
    with pytest.raises(errors.FileFormatValidationError):
        some_validator.validate_bag(
            str(EXAMPLE_BAG_WORKING_PATH)
        )

    pattern_occurs, _ = pattern_in_list_of_strings(
        r".*File Extension Validator.*unknown type or invalid extension.*",
        str(some_validator.log.pick(Context.ERROR)).split("\n")
    )

    assert pattern_occurs

def test_file_format_validate_file():
    """Test `file_format.validate_file`-method individually."""

    # load profile into validator
    some_validator = file_format.FileFormatValidator(
        [(r"image/.*", example.ExamplePlugin())]
    )
    # and make a copy of a valid example bag
    duplicate_example_bag()

    # select file to validate
    bag_payload_file = \
        EXAMPLE_BAG_WORKING_PATH \
            / "data" \
            / "preservation_master" \
            / "sample.png"

    exitcode = some_validator.validate_file(bag_payload_file)

    assert exitcode == 0
