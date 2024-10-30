"""
This module contains pytest-tests for testing the features of the
payload_structure-component.

Tests use custom built test-bags (payload structure-wise) and assert
changes made to that working directory.
"""


import shutil
from pathlib import Path
from copy import deepcopy

import pytest
from dcm_common import util, LoggingContext as Context

from dcm_bag_validator import errors, payload_structure


EXAMPLE_BAG_FIXTURE_PATH = \
    Path("test_dcm_bag_validator/fixtures/example_bag")
EXAMPLE_BAG_WORKING_PATH = Path("tmp/example_bag_copy")
#PAYLOAD_PROFILE_FIXTURE_PATH = \
#    Path("test_dcm_bag_validator/fixtures/payload_profile.json")
MINIMAL_PROFILE = {
        "Payload-Folders-Required": [
            "required_directory"
        ],
        "Payload-Folders-Allowed": [
            "required_directory", {
                "regex": r"optional_directory/\d+",
                "example": "optional_directory/4" # only for this test module
            }
        ]
    }

def generate_example_bag():
    """Generate the example bag in fixtures to (cleaned) working dir."""

    if EXAMPLE_BAG_WORKING_PATH.is_dir():
        shutil.rmtree(EXAMPLE_BAG_WORKING_PATH)

    # generate basic test-bag directory structure
    bag_data = EXAMPLE_BAG_WORKING_PATH / "data"
    for required in MINIMAL_PROFILE["Payload-Folders-Required"]:
        (bag_data / required).mkdir(parents=True, exist_ok=True)
        util.write_test_file(bag_data / required / "dummy.txt")

    for allowed in MINIMAL_PROFILE["Payload-Folders-Allowed"]:
        if isinstance(allowed, dict):
            (bag_data / allowed["example"]).mkdir(parents=True, exist_ok=True)
            util.write_test_file(bag_data / allowed["example"] / "dummy.doc")
        else:
            (bag_data / allowed).mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session", autouse=True)
def cleanup(request):
    """Cleanup a testing directory once we are finished."""

    def remove_test_dir():
        if EXAMPLE_BAG_WORKING_PATH.is_dir():
            shutil.rmtree(EXAMPLE_BAG_WORKING_PATH)
        if EXAMPLE_BAG_WORKING_PATH.parent.is_dir():
            EXAMPLE_BAG_WORKING_PATH.parent.rmdir()
    request.addfinalizer(remove_test_dir)

@pytest.fixture(name="minimal_profile")
def fixture_minimal_profile():
    """Provide a minimal payload profile for testing."""
    payload_profile_url = "MINIMAL_PROFILE"
    return payload_profile_url, MINIMAL_PROFILE

def test_valid_bag(minimal_profile):
    """Test valid bag."""
    # load profile into validator object
    some_validator = payload_structure.PayloadStructureValidator(
        url=minimal_profile[0],
        profile=minimal_profile[1]
    )

    # and make a copy of a valid example bag
    generate_example_bag()

    # test bag format
    assert some_validator.validate_bag(
        str(EXAMPLE_BAG_WORKING_PATH)
    ) == 0

def test_invalid_bag_required_but_not_allowed_directory(
    minimal_profile, pattern_in_list_of_strings
):
    """Test bag in which a required directory is also not allowed."""
    # load profile into validator object
    modified_profile = deepcopy(minimal_profile[1])
    modified_profile["Payload-Folders-Required"].append("not_allowed")
    some_validator = payload_structure.PayloadStructureValidator(
        url=minimal_profile[0],
        profile=modified_profile
    )

    # and make a copy of a valid example bag
    generate_example_bag()

    # make additional required directory
    (EXAMPLE_BAG_WORKING_PATH / "data" / "not_allowed").mkdir()


    # test bag format
    with pytest.raises(errors.PayloadStructureValidationError):
        some_validator.validate_bag(
            str(EXAMPLE_BAG_WORKING_PATH)
        )

    pattern_occurs, _ = pattern_in_list_of_strings(
        r".*Payload Structure Validator.*Required payload directory '.*' not listed in Payload-Folders-Allowed.*",
        str(some_validator.log.pick(Context.ERROR)).split("\n")
    )
    assert pattern_occurs

def test_invalid_bag_missing_required_directory(
    minimal_profile, pattern_in_list_of_strings
):
    """Test bag in which a required directory is missing."""
    # load profile into validator object
    some_validator = payload_structure.PayloadStructureValidator(
        url=minimal_profile[0],
        profile=minimal_profile[1]
    )

    # and make a copy of a valid example bag
    generate_example_bag()

    RENAME_PATH = EXAMPLE_BAG_WORKING_PATH / "data" \
        / minimal_profile[1]["Payload-Folders-Required"][0]

    RENAME_PATH.rename(str(RENAME_PATH) + "_bad")

    # test bag format
    with pytest.raises(errors.PayloadStructureValidationError):
        some_validator.validate_bag(
            str(EXAMPLE_BAG_WORKING_PATH)
        )

    pattern_occurs, _ = pattern_in_list_of_strings(
        r".*Payload Structure Validator.*Required payload directory '.*' is not present in Bag.*",
        str(some_validator.log.pick(Context.ERROR)).split("\n")
    )
    assert pattern_occurs
    pattern_occurs, _ = pattern_in_list_of_strings(
        r".*Payload Structure Validator.*File '.*' found in illegal location of payload directory.*",
        str(some_validator.log.pick(Context.ERROR)).split("\n")
    )
    assert pattern_occurs

def test_invalid_bag_files_in_every_directory(
    minimal_profile, pattern_in_list_of_strings
):
    """Test bag in which every directory contains a file
    (assuming not all directories are allowed)."""
    # load profile into validator object
    some_validator = payload_structure.PayloadStructureValidator(
        url=minimal_profile[0],
        profile=minimal_profile[1]
    )

    # and make a copy of a valid example bag
    generate_example_bag()

    # iterate through directory
    dir_list = util.list_directory_content(
        EXAMPLE_BAG_WORKING_PATH,
        pattern="**/*",
        condition_function=lambda p : p.is_dir()
    )
    for some_dir in dir_list:
        util.write_test_file(some_dir / "test.dat")

    # test bag format
    with pytest.raises(errors.PayloadStructureValidationError):
        some_validator.validate_bag(
            str(EXAMPLE_BAG_WORKING_PATH)
        )

    _, match_count = pattern_in_list_of_strings(
        r".*Payload Structure Validator.*File '.*' found in illegal location of payload directory.*",
        str(some_validator.log.pick(Context.ERROR)).split("\n")
    )

    assert match_count == 2

def test_invalid_bag_files_in_certain_directory(
    minimal_profile, pattern_in_list_of_strings
):
    """Test addition of slash in regex for allowed directories (e.g. if
    Payload-Folders-Allowed reads 'allowed_dir/[0-9]' exclude files
    named 'allowed_dir/4a.dat' and similar)."""
    # load profile into validator object
    some_validator = payload_structure.PayloadStructureValidator(
        url=minimal_profile[0],
        profile=minimal_profile[1]
    )

    # and make a copy of a valid example bag
    generate_example_bag()

    util.write_test_file(
        EXAMPLE_BAG_WORKING_PATH \
            / "data" \
            / "optional_directory" \
            / "4" \
            / "test.dat",
        mkdir=True
    )
    util.write_test_file(
        EXAMPLE_BAG_WORKING_PATH \
            / "data" \
            / "optional_directory" \
            / "4atest.dat",
        mkdir=True
    )
    util.write_test_file(
        EXAMPLE_BAG_WORKING_PATH \
            / "data" \
            / "optional_directory" \
            / "4a" \
            / "test.dat",
        mkdir=True
    )

    # test bag format
    with pytest.raises(errors.PayloadStructureValidationError):
        some_validator.validate_bag(
            str(EXAMPLE_BAG_WORKING_PATH)
        )

    _, match_count = pattern_in_list_of_strings(
        r".*Payload Structure Validator.*File '.*' found in illegal location of payload directory.*",
        str(some_validator.log.pick(Context.ERROR)).split("\n")
    )

    assert match_count == 2

def test_invalid_bag_files_in_certain_directory_noregex(
    minimal_profile, pattern_in_list_of_strings
):
    """Test addition of slash in string (no regex-variant) for allowed
    directories (e.g. if Payload-Folders-Allowed reads 'required_dir'
    exclude files named 'required_dir_a.dat' and similar)."""
    # load profile into validator object
    some_validator = payload_structure.PayloadStructureValidator(
        url=minimal_profile[0],
        profile=minimal_profile[1]
    )

    # and make a copy of a valid example bag
    generate_example_bag()

    util.write_test_file(
        EXAMPLE_BAG_WORKING_PATH \
            / "data" \
            / "required_directory_test.dat",
        mkdir=True
    )
    util.write_test_file(
        EXAMPLE_BAG_WORKING_PATH \
            / "data" \
            / "required_directory" \
            / "test.dat",
        mkdir=True
    )

    # test bag format
    with pytest.raises(errors.PayloadStructureValidationError):
        some_validator.validate_bag(
            str(EXAMPLE_BAG_WORKING_PATH)
        )

    pattern_occurs, _ = pattern_in_list_of_strings(
        r".*Payload Structure Validator.*File '.*' found in illegal location of payload directory.*",
        str(some_validator.log.pick(Context.ERROR)).split("\n")
    )
    assert pattern_occurs

def test_invalid_bag_filenames_differ_only_by_capitalization(
    minimal_profile, pattern_in_list_of_strings
):
    """Test bag in which the names of two files differ only in
    capitalization."""
    # load profile into validator object
    some_validator = payload_structure.PayloadStructureValidator(
        url=minimal_profile[0],
        profile=minimal_profile[1]
    )

    # and make a copy of a valid example bag
    generate_example_bag()

    # write two test files
    util.write_test_file(
        EXAMPLE_BAG_WORKING_PATH \
            / "data" \
            / "required_directory" \
            / "test.dat",
        mkdir=True
    )
    util.write_test_file(
        EXAMPLE_BAG_WORKING_PATH \
            / "data" \
            / "required_directory" \
            / "TEST.dat",
        mkdir=True
    )

    # test bag format
    with pytest.raises(errors.PayloadStructureValidationError):
        some_validator.validate_bag(
            str(EXAMPLE_BAG_WORKING_PATH)
        )

    pattern_occurs, _ = pattern_in_list_of_strings(
        r".*Payload Structure Validator.*File '.*' and '.*' only differ in their capitalization.*",
        str(some_validator.log.pick(Context.ERROR)).split("\n")
    )
    assert pattern_occurs
