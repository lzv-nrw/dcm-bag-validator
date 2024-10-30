"""
Python module containing a derived and extended
version of the BagIt-validator-package
https://github.com/bagit-profiles/bagit-profiles-validator

This module has been developed in the LZV.nrw-project.
"""

from typing import Optional
import re
import sys
from pathlib import Path

from bagit_profile import Profile, ProfileValidationReport
import bagit
from dcm_common import util, LoggingContext as Context, Logger
from dcm_common.util import NestedDict

from dcm_bag_validator import errors


class ProfileValidator(Profile):
    """
    This class is derived from the Profile-class in the
    bagit_profile-package for use in the LZV.nrw-project.

    The constructor expects a url or local path for a BagIt-profile.
    A validation on an existing bag can be performed by means of the
    validate_bag-method by supplying a path to the bag.

    Keyword arguments:
    url -- file path or url to the desired BagIt-profile.
    profile -- already instanciated BagIt-profile as dictionary
               (default None)
    ignore_baginfo_tag_case -- whether or not to use case sensitive
                               tags in profile (default False)
    """

    VALIDATOR_TAG = "Profile Validator"
    VALIDATOR_SUMMARY = "validation of BagIt-Bags against a bagit-profile"
    VALIDATOR_DESCRIPTION = \
        "This validator extendeds the BagIt-profiles-validator: " \
        + "https://github.com/bagit-profiles/bagit-profiles-validator " \
        + "The validation includes the Bag's serialization and the metadata " \
        + "format in 'baginfo.txt'."
    NEGATIVE_RESPONSE_BAGITTXT = "\033[31mDirectory does not contain "\
        "required file 'bagit.txt'.\033[0m"
    NEGATIVE_RESPONSE_BAGITTXT_INFO = "\033[31mNo valid bag instance, "\
        "can't proceed with profile validation.\033[0m"
    POSITIVE_RESPONSE_SER = "\033[32mPayload serialization is ok.\033[0m"
    NEGATIVE_RESPONSE_SER = "\033[31mSerialization is not ok.\033[0m"
    POSITIVE_RESPONSE_PRO = "\033[32mBag conforms to profile\033[0m ({url})."
    NEGATIVE_RESPONSE_PRO = "\033[31mBag does not conform to "\
        "profile\033[0m ({url})."

    def __init__(
        self,
        url: str,
        profile: Optional[NestedDict] = None,
        ignore_baginfo_tag_case: bool = False
    ) -> None:
        super().__init__(str(url), profile, ignore_baginfo_tag_case)
        self.log: Optional[Logger] = None
        self.report: Optional[ProfileValidationReport]

    def get_profile(self) -> NestedDict:
        """Return the profile in self.url (JSON-format) as dictionary."""

        return util.get_profile(self.url)

    def validate_bag(
            self,
            bag_path: str | Path,
            test_serialization: bool = True,
            test_profile: bool = True,
            report_back: bool = True
    ) -> int:
        """
        This method executes the validation-logic of the ProfileValidator.

        Returns 0 on full conformity and raises a ProfileValidationError
        in case of non-conformity.

        Keyword arguments:
        bag_path -- file path to the bag to be validated either as
                    string literal or pathlib Path
        test_serialization -- whether or not to test for serialization
                              (default True)
        test_profile -- whether or not to test profile conformity
                        (default True)
        report_back -- whether or not to print a test result
                       (default True)
        """

        # setup log
        self.log = Logger(default_origin=self.VALIDATOR_TAG)

        exitcode = 0
        some_validation_error = None

        # instantiate bag
        bag = None
        try:
            if isinstance(bag_path, str):
                bag = bagit.Bag(bag_path)
            elif isinstance(bag_path, Path):
                bag = bagit.Bag(str(bag_path))
            else:
                raise TypeError(
                    "Argument 'bag_path' is expected to be either "
                    "pathlib Path or str. Found " + str(type(bag_path)) + "."
                )
        except bagit.BagError as exc_info:
            if "Expected bagit.txt does not exist" in str(exc_info):
                self.log.log(
                    Context.ERROR,
                    body=self.NEGATIVE_RESPONSE_BAGITTXT
                )
                self.log.log(
                    Context.INFO,
                    body=self.NEGATIVE_RESPONSE_BAGITTXT_INFO
                )
            else:
                raise exc_info
            exitcode = 1
            some_validation_error = \
                errors.ValidationError(".")

        if bag is not None:
            # check whether payload is serialized
            if test_serialization:
                if self.validate_serialization(bag_path):
                    self.log.log(
                        Context.INFO,
                        body=self.POSITIVE_RESPONSE_SER
                    )
                else:
                    self.log.log(
                        Context.INFO,
                        body=self.NEGATIVE_RESPONSE_SER
                    )
                    self.log.log(
                        Context.ERROR,
                        body=self.NEGATIVE_RESPONSE_SER
                    )
                    exitcode = 1
                    some_validation_error = \
                        errors.SerializationValidationError(".")

            # check bag against BagIt-profile
            if test_profile:
                if self.validate(bag):
                    self.log.log(
                        Context.INFO,
                        body=self.POSITIVE_RESPONSE_PRO.format(url=self.url)
                    )
                else:
                    self.log.log(
                        Context.INFO,
                        body=self.NEGATIVE_RESPONSE_PRO.format(url=self.url)
                    )
                    exitcode = 1
                    if some_validation_error is None:
                        some_validation_error = errors.ProfileValidationError(
                            "."
                        )

            # rewrite error messages to a shorter format
            # this is needed since the bagit_profile-library uses the less-
            # helpful __str__-method of bagit.bag
            if self.report:
                # mypy - hint
                assert self.report is not None
                # add bagit_profile internally logged errors to Logger
                self.log.log(
                    Context.ERROR,
                    body=list(
                        map(
                            lambda x: x.replace(str(bag) + ": ", ""),
                            self.report.errors
                        )
                    )
                )

        # detailed report on problems
        if report_back:
            if self.log:
                print(self.log.fancy(), file=sys.stderr)

        # raise exception if necessary
        if exitcode != 0:
            # mypy - hint
            assert some_validation_error is not None
            raise type(some_validation_error)(
                "At least one error occurred during validation: "
                + str(self.log).replace("\n", " ")
            )
        return exitcode

    def _fail(self, msg: str) -> None:
        """
        Add message to self.report.errors.

        This method is executed if some check of the provided bag fails.
        The message is then appended to the log in self.report.errors .

        Keyword arguments:
        msg -- message string
        """

        # mypy - hint
        assert isinstance(self.report, ProfileValidationReport)
        # only append to report.errors instead
        # of raising ProfileValidationError
        self.report.errors.append(msg)

    def validate_bag_info(self, bag: bagit.Bag) -> bool:
        """
        Validate bag-info.txt with profile.

        This method extends the original bagit_profile-validation method
        for the bag-info.txt with additional checks using regex.

        Keyword arguments:
        bag -- instance of an LOC-bag to be validated
        """

        # execute bagit_profile-validation method
        super().validate_bag_info(bag)

        # now perform custom tests in the same format as in
        # bagit_profile-package's validate_bag_info-method
        # to this end, first repeat collection of bag_info
        # (duplicated from bagit_profile-package)
        # First, check to see if bag-info.txt exists.
        path_to_baginfotxt = Path(bag.path) / "bag-info.txt"
        if not path_to_baginfotxt.is_file():
            self._fail(f"{bag}: bag-info.txt is not present.")
        # Then check for the required 'BagIt-Profile-Identifier' tag and
        # ensure it has the same value as self.url.
        if self.ignore_baginfo_tag_case:
            bag_info = {self.normalize_tag(k): v for k, v in bag.info.items()}
        else:
            bag_info = bag.info

        # now test format of description tag
        for tag in self.profile["Bag-Info"]:
            normalized_tag = self.normalize_tag(tag)
            config = self.profile["Bag-Info"][tag]
            if "description" in config and normalized_tag in bag_info:
                # enter all values into a list to check with description
                # individually afterwards
                if isinstance(bag_info[normalized_tag], list):
                    values = bag_info[normalized_tag]
                else:
                    values = [bag_info[normalized_tag]]
                # now check for matching regex/description
                for value in values:
                    if not re.fullmatch(config["description"],
                                        value):
                        self._fail(
                                f"{bag}: Description Tag {tag} is present in "
                                + "bag-info.txt but its value is not "
                                + f"allowed: ('{value}')."
                            )
        return True
