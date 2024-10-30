"""
This module contains pytest-tests for testing the features of the
payload_integrity-component.

Tests use custom built test-bags (payload structure-wise) and assert
changes made to that working directory.
"""


import shutil
from pathlib import Path
import pytest

from dcm_common import util, LoggingContext as Context

from dcm_bag_validator import errors, payload_integrity


EXAMPLE_BAG_FIXTURE_PATH = \
    Path("test_dcm_bag_validator/fixtures/example_bag")
EXAMPLE_BAG_WORKING_PATH = Path("tmp/example_bag_copy")

def duplicate_example_bag():
    """Generate the example bag in fixtures to (cleaned) working dir."""

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

def test_valid_bag():
    """Test valid bag."""
    # load profile into validator object
    some_validator = payload_integrity.PayloadIntegrityValidator()

    # and make a copy of a valid example bag
    duplicate_example_bag()

    # test bag format
    assert some_validator.validate_bag(
            str(EXAMPLE_BAG_WORKING_PATH)
        ) == 0

def test_invalid_bag_unexpected_file_in_payload(pattern_in_list_of_strings):
    """Test bag in which a required directory has been removed."""
    # load profile into validator object
    some_validator = payload_integrity.PayloadIntegrityValidator()

    # and make a copy of a valid example bag
    duplicate_example_bag()

    UNEXPECTED_FILE_PATH = \
        EXAMPLE_BAG_WORKING_PATH / "data" / "preservation_master" \
        / "unxpctd.txt"

    util.write_test_file(UNEXPECTED_FILE_PATH)

    # test bag format
    with pytest.raises(errors.PayloadIntegrityValidationError):
        some_validator.validate_bag(
            str(EXAMPLE_BAG_WORKING_PATH)
        )

    pattern_occurs, _ = pattern_in_list_of_strings(
        r".*Payload Integrity Validator.*Payload-Oxum validation failed.*",
        str(some_validator.log.pick(Context.ERROR)).split("\n")
    )
    assert pattern_occurs
    pattern_occurs, _ = pattern_in_list_of_strings(
        r".*Payload Integrity Validator.*exists on filesystem but is not in the manifest.*",
        str(some_validator.log.pick(Context.ERROR)).split("\n")
    )
    assert pattern_occurs

def test_invalid_bag_missing_file_in_payload(pattern_in_list_of_strings):
    """Test bag in which a required directory has been removed."""
    # load profile into validator object
    some_validator = payload_integrity.PayloadIntegrityValidator()

    # and make a copy of a valid example bag
    duplicate_example_bag()

    DELETED_FILE_PATH = \
        EXAMPLE_BAG_WORKING_PATH / "data" / "preservation_master"
    shutil.rmtree(DELETED_FILE_PATH)

    # test bag format
    with pytest.raises(errors.PayloadIntegrityValidationError):
        some_validator.validate_bag(
            str(EXAMPLE_BAG_WORKING_PATH)
        )

    pattern_occurs, _ = pattern_in_list_of_strings(
        r".*Payload Integrity Validator.*Payload-Oxum validation failed.*",
        str(some_validator.log.pick(Context.ERROR)).split("\n")
    )
    assert pattern_occurs
    pattern_occurs, _ = pattern_in_list_of_strings(
        r".*Payload Integrity Validator.*exists in manifest but was not found on filesystem.*",
        str(some_validator.log.pick(Context.ERROR)).split("\n")
    )
    assert pattern_occurs
    pattern_occurs, _ = pattern_in_list_of_strings(
        r".*Payload Integrity Validator.*(md5|sha1|sha256|sha512) validation failed.*",
        str(some_validator.log.pick(Context.ERROR)).split("\n")
    )
    assert pattern_occurs
