"""
Test suite for the bagit_profile-validation module.
"""

from unittest import mock

import pytest
from bagit_profile import ProfileValidationReport
from dcm_common import LoggingContext as Context

from dcm_bag_validator.bagit_profile import ProfileValidator
from dcm_bag_validator import errors

@pytest.fixture(name="profile_identifier")
def _profile_identifier():
    return "profile-identifier"


@pytest.fixture(name="bagit_profile_info")
def _baginfo_profile_info(profile_identifier):
    return {
        "Source-Organization": "",
        "External-Description": "",
        "Version": "",
        "BagIt-Profile-Identifier": profile_identifier
    }


def test_get_profile(bagit_profile_info):
    """
    Test method `get_profile` of `ProfileValidator`.
    """

    # setup patcher
    patcher = mock.patch(
        "dcm_bag_validator.bagit_profile.util.get_profile",
        side_effect=lambda *args, **kwargs: {
            "url": args[0], "BagIt-Profile-Info": bagit_profile_info
        }
    )

    patcher.start()

    # setup validator and check for generated fake profile
    validator = ProfileValidator("")
    assert validator.profile["url"] == validator.url

    validator.url = "url"
    new_profile = validator.get_profile()
    assert new_profile["url"] == validator.url

    patcher.stop()


def test_validate_bag_bad_bag(profile_identifier, bagit_profile_info):
    """
    Test method `validate_bag` of `ProfileValidator` with bad Bag.
    """

    # setup validator (with profile including property with description-tag)
    validator = ProfileValidator(
        profile_identifier, profile={
            "BagIt-Profile-Info": bagit_profile_info,
        }
    )
    validator.report = ProfileValidationReport()

    # run test
    with pytest.raises(errors.ValidationError):
        validator.validate_bag(
            ".",
            report_back=False
        )


def test_validate_bag_basic(profile_identifier, bagit_profile_info):
    """
    Test method `validate_bag` of `ProfileValidator` with faked
    functionality in bagit_profile.Profile
    """

    # fake serialization
    patcher_serialization = mock.patch(
        "bagit_profile.Profile.validate_serialization",
        side_effect=lambda *args, **kwargs: True
    )

    # fake validate
    patcher_validation = mock.patch(
        "bagit_profile.Profile.validate",
        side_effect=lambda *args, **kwargs: True
    )

    # setup validator
    validator = ProfileValidator(
        profile_identifier, profile={
            "BagIt-Profile-Info": bagit_profile_info,
        }
    )

    # check for generated fake profile
    patcher_serialization.start()
    patcher_validation.start()

    validator.report = ProfileValidationReport()

    exit_code = validator.validate_bag(
        "",
        report_back=False
    )

    patcher_serialization.stop()
    patcher_validation.stop()

    assert exit_code == 0


@pytest.mark.parametrize(
    (
        "test_serialization", "serialization_ok", "validation_ok",
        "expected_result"
    ),
    [
        (True, True, True, 0),
        (False, True, True, 0),
        (False, False, True, 0),
        (True, False, True, 1),
        (True, True, False, 1),
        (True, False, False, 1),
    ],
    ids=[
        "s11n-check_ok", "s11n-no-check_ok", "s11n-no-check_not-ok",
        "s11n-check_not-ok", "s11n-ok_invalid", "s11n-not-ok_invalid"
    ]
)
def test_validate_bag_serialization_and_validate(
    profile_identifier, bagit_profile_info,
    test_serialization, serialization_ok, validation_ok, expected_result
):
    """
    Test method `validate_bag` of `ProfileValidator` regarding
    `bagit_profile.Profile.validate_serialization` and
    `bagit_profile.Profile.validate` with faked functionality in
    `bagit_profile.Profile`.
    """

    # fake serialization
    patcher_serialization = mock.patch(
        "bagit_profile.Profile.validate_serialization",
        side_effect=lambda *args, **kwargs: serialization_ok
    )

    # fake validate
    patcher_validation = mock.patch(
        "bagit_profile.Profile.validate",
        side_effect=lambda *args, **kwargs: validation_ok
    )

    # setup validator
    validator = ProfileValidator(
        profile_identifier, profile={
            "BagIt-Profile-Info": bagit_profile_info,
        }
    )

    # check for generated fake profile
    patcher_serialization.start()
    patcher_validation.start()

    validator.report = ProfileValidationReport()

    try:
        exit_code = validator.validate_bag(
            "",
            test_serialization=test_serialization,
            report_back=False
        )
    except errors.ValidationError as exc_info:
        if not serialization_ok:
            assert isinstance(exc_info, errors.SerializationValidationError)
        else:
            assert isinstance(exc_info, errors.ProfileValidationError)
    else:
        assert exit_code == expected_result

    patcher_serialization.stop()
    patcher_validation.stop()


def test_validate_bag_report(profile_identifier, bagit_profile_info):
    """
    Test method `validate_bag` of `ProfileValidator` regarding the
    generation of a report from the `bagit_profile.Profile` reports.
    """

    # setup validator
    validator = ProfileValidator(
        profile_identifier, profile={
            "BagIt-Profile-Info": bagit_profile_info,
        }
    )

    # prepare report for generating fake message
    validator.report = ProfileValidationReport()
    test_message = "test message"
    def fake_validate(*args, **kwargs):
        validator._fail(test_message)
        return False

    # fake validate
    patcher_validation = mock.patch(
        "bagit_profile.Profile.validate",
        side_effect=fake_validate
    )

    patcher_validation.start()

    # run test
    with pytest.raises(errors.ProfileValidationError):
        validator.validate_bag(
            "",
            test_serialization=False,
            report_back=False
        )

    log = validator.log[Context.ERROR]
    assert len(log) == 1
    assert test_message in log[0].body


def test_validate_bag_info(profile_identifier, bagit_profile_info):
    """
    Test `validate_bag_info` of `ProfileValidator` regarding LZV.nrw-
    specific description-feature (fake other components like
    `bagit_profile.Profile.validate_bag_info` and `pathlib.Path.is_file`).
    """

    # fake validate
    patcher_validation = mock.patch(
        "bagit_profile.Profile.validate_bag_info",
        side_effect=lambda *args, **kwargs: True
    )
    # fake Path.is_file()
    patcher_path = mock.patch(
        "pathlib.Path.is_file",
        side_effect=lambda *args, **kwargs: True
    )

    # setup validator (with profile including property with description-tag)
    validator = ProfileValidator(
        profile_identifier, profile={
            "BagIt-Profile-Info": bagit_profile_info,
            "Bag-Info": {
                "Property": {
                    "description": r"[0-9]*"
                },
            }
        }
    )
    validator.report = ProfileValidationReport()

    # fake bag-object
    class FakeBag:
        def __init__(self, path, info):
            self.path = path
            self.info = info

    patcher_validation.start()
    patcher_path.start()

    # run test with two values (only "1" is allowed accoring to profile)
    bad_value = "bad-value"
    validator.validate_bag_info(FakeBag("", {"Property": [bad_value, "1"]}))

    assert len(validator.report.errors) == 1
    assert "value is not allowed" in validator.report.errors[0]
    assert bad_value in validator.report.errors[0]

    patcher_validation.stop()
    patcher_path.stop()
