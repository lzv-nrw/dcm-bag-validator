"""
Python module defining the PayloadIntegrityValidator-class which
can be used to validate a BagIt-Bag's payload integrity.

This module has been developed in the LZV.nrw-project.
"""

from typing import Optional
import sys
from pathlib import Path

import bagit
from dcm_common import LoggingContext as Context, Logger

from dcm_bag_validator import errors


class PayloadIntegrityValidator():
    """
    This class defines the validator for payload integrity, i.e.
    completeness and agreement of checksums with manifests.

    A validation (existence and checksums) on an existing bag can be
    performed by means of the validate_bag-method by supplying a path
    to the bag.
    """

    VALIDATOR_TAG = "Payload Integrity Validator"
    VALIDATOR_SUMMARY = "validation of BagIt-Bags' payload integrity"
    VALIDATOR_DESCRIPTION = \
        "This validator validates a BagIt-Bag's payload with respect to " \
        + "completeness and file integrity by using the functionality " \
        + "provided by the loc-bagit library: " \
        + "https://github.com/LibraryOfCongress/bagit-python"
    NEGATIVE_RESPONSE_BAGITTXT = "\033[31mDirectory does not contain "\
        "required file 'bagit.txt'.\033[0m"
    NEGATIVE_RESPONSE_BAGITTXT_INFO = "\033[31mNo valid bag instance, "\
        "can't proceed with checksum validation.\033[0m"
    POSITIVE_RESPONSE = "\033[32mBag's payload checksums conform to "\
                "manifest information.\033[0m"
    NEGATIVE_RESPONSE = "\033[31mBag's payload checksums do not conform to "\
                "manifest information or missing files.\033[0m"

    def __init__(self) -> None:
        self.log: Optional[Logger] = None

    def validate_bag(
        self,
        bag_path: str | Path,
        report_back: bool = True
    ) -> int:
        """
        This method executes the validation-logic of the
        PayloadIntegrityValidator.

        Returns 0 on full conformity and raises a
        PayloadIntegrityValidationError in case of non-conformity.

        Keyword arguments:
        bag_path -- file path to the bag to be validated either as
                    string literal or pathlib Path
        report_back -- whether or not to print a test result
                       (default True)
        """

        # setup log
        self.log = Logger(default_origin=self.VALIDATOR_TAG)

        exitcode = 0

        # instantiate bag
        bag = None
        try:
            if isinstance(bag_path, str):
                bag = bagit.Bag(bag_path)
            elif isinstance(bag_path, Path):
                bag = bagit.Bag(str(bag_path))
            else:
                raise TypeError("Argument 'bag_path' is expected to be either "\
                    "pathlib Path or str. Found " + str(type(bag_path)) + ".")
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

        if bag is not None:
            thisexitcode = 0
            # validate payload checksums + missing files using bagit-library
            # perform a series of internal validation steps
            for validation_step in [
                    [bag._validate_contents, {
                        "processes": 1,
                        "fast": False,
                        "completeness_only": False
                    }],
                    [bag._validate_completeness, {}],
                    [bag._validate_entries, {"processes": 1}]
            ]:
                try:
                    validation_step[0](**validation_step[1])
                except (bagit.BagError, ValueError) as err:
                    if isinstance(err, ValueError):
                        # ValueError is being caught here since sometimes bagit
                        # does not check if input has valid format (e.g.
                        # Payload-Oxum)
                        self.log.log(
                            Context.ERROR,
                            body="Bad input for some internal bagit-method."
                        )
                    else:
                        # reformat and append output from bagit-library
                        errlist = str(err).split("\n")
                        for entry in errlist:
                            self.log.log(
                                Context.ERROR,
                                body=entry.strip("WARNING")
                            )
                    thisexitcode = 1

            # print verdict
            if not thisexitcode:
                message = self.POSITIVE_RESPONSE
            else:
                exitcode = 1
                message = self.NEGATIVE_RESPONSE
            self.log.log(
                Context.INFO,
                body=message
            )

        # detailed log on problems
        if report_back:
            print(self.log.fancy(), file=sys.stderr)

        # raise exception if necessary
        if exitcode != 0:
            raise errors.PayloadIntegrityValidationError(
                "At least one error occurred during payload integrity "
                + "validation: "
                + str(self.log).replace("\n", " ")
            )

        return exitcode
