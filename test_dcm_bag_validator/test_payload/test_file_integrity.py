"""
Test suite for the `FileIntegrityValidator`-class
"""

from pathlib import Path

import pytest

from dcm_bag_validator import file_integrity, errors


@pytest.fixture(name="test_file_info")
def _test_file_info():
    return Path("test_dcm_bag_validator/fixtures/example_bag/data/preservation_master/sample.png"), "md5", "45c364570527d9bde2fee474a475c911"


def test_validate_file_valid(test_file_info):
    """Test method `validate_file` of `FileIntegrityValidator`."""

    validator = file_integrity.FileIntegrityValidator()
    assert validator.validate_file(
        test_file_info[0],
        False,
        test_file_info[1],
        test_file_info[2]
    ) == 0


def test_validate_file_invalid(test_file_info):
    """Test method `validate_file` of `FileIntegrityValidator`."""

    validator = file_integrity.FileIntegrityValidator()
    with pytest.raises(errors.PayloadIntegrityValidationError):
        validator.validate_file(
            test_file_info[0],
            False,
            test_file_info[1],
            test_file_info[2] + "a"
        )


def test_validate_file_method_override(test_file_info):
    """Test method `validate_file` of `FileIntegrityValidator`."""

    validator = file_integrity.FileIntegrityValidator(method="sha1")
    assert validator.validate_file(
        test_file_info[0],
        False,
        test_file_info[1],
        test_file_info[2]
    ) == 0


def test_bad_method(test_file_info):
    """Test `FileIntegrityValidator` when using bad method str."""

    with pytest.raises(ValueError):
        validator = file_integrity.FileIntegrityValidator(
            test_file_info[1] + "a",
            test_file_info[2]
        )
        validator.validate_file(
            test_file_info[0],
            False
        )
    with pytest.raises(ValueError):
        validator = file_integrity.FileIntegrityValidator()
        validator.validate_file(
            test_file_info[0],
            False,
            test_file_info[1] + "a",
            test_file_info[2]
        )
    with pytest.raises(ValueError):
        validator = file_integrity.FileIntegrityValidator()
        validator.validate_file(
            test_file_info[0],
            False
        )
