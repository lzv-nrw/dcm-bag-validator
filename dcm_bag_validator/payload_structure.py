"""
Python module defining the PayloadStructureValidator-class which
can be used to validate a BagIt-Bag's payload against its specification.

This module has been developed in the LZV.nrw-project.
"""

from typing import TypedDict, TypeAlias, Mapping, Optional
import sys
from pathlib import Path
import re

from dcm_common import util, LoggingContext as Context, Logger

from dcm_bag_validator import errors


# define types for typehinting of typed dictionaries
class RegexDict(TypedDict):
    regex: str
class PayloadFolderDict(TypedDict):
    string: str
    is_regex: bool
# define json-format
NestedDict: TypeAlias = Mapping[str, "str | list[str] | NestedDict"]

class PayloadStructureValidator():
    """
    This class defines the validator for the payload directory structure
    introduced in the LZV.nrw-project.

    The constructor expects a url or local path to a Payload-structure
    -profile. A validation on an existing bag can be performed by means
    of the validate_bag-method by supplying a path to the bag.

    Keyword arguments:
    url -- file path or url to the desired BagIt-profile.
    profile -- already instanciated BagIt-profile as dictionary
               (default None)
    ignore_baginfo_tag_case -- whether or not to use case sensitive
                               tags in profile (default False)
    """

    VALIDATOR_TAG = "Payload Structure Validator"
    VALIDATOR_SUMMARY = \
        "validation of BagIt-Bags against a bagit-payload-profile"
    VALIDATOR_DESCRIPTION = \
        "This validator uses a payload-profile to validate the expected file" \
        + "system structure in the payload directory of a BagIt-Bag. This " \
        + "validation includes the (required or allowed) existence of " \
        + "directories."
    POSITIVE_RESPONSE_ALLOW_REQ = "\033[32mBag's payload's root directories "\
        "conform to profile\033[0m ({url})."
    NEGATIVE_RESPONSE_ALLOW_REQ = "\033[31mBag's payload's root directories "\
        "do not conform to profile\033[0m ({url})."
    POSITIVE_RESPONSE_STRUCT = "\033[32mBag's payload directory structure "\
        "conforms to profile.\033[0m"
    NEGATIVE_RESPONSE_STRUCT = "\033[31mBag's payload directory structure "\
        "does not conform to profile.\033[0m"
    POSITIVE_RESPONSE_CAP = "\033[32mBag's payload filenames' capitalization "\
        "is fine.\033[0m"
    NEGATIVE_RESPONSE_CAP = "\033[31mBag's payload filenames' capitalization "\
        "is problematic.\033[0m"

    def __init__(self, url: str, profile: Optional[NestedDict] = None) -> None:
        self.url = str(url)

        self.profile: NestedDict
        if isinstance(profile, dict):
            self.profile = profile
        else:
            self.profile = self.get_profile()

        # read up on some information from profile content
        # used to handle the varying types of values under the common key
        # 'Payload-Folders-Allowed'
        def process_allowed_regex_from_profile(
            input_value: str | RegexDict
        ) -> PayloadFolderDict:
            """
            Returns a dict with the two keys 'string' and 'is_regex' to
            consistently process allowed and required directories in
            payload profile.

            Keyword arguments:
            input_value -- input as read from json; either string literal or
                        dict containing the key 'regex'
            """

            if isinstance(input_value, dict):
                return {
                    "string": input_value["regex"]
                        + ("/" if input_value["regex"][-1] != "/" else ""),
                    "is_regex": True
                }

            return {
                "string": input_value
                        + ("/" if input_value[-1] != "/" else ""),
                "is_regex": False
            }

        self.allowed: list[PayloadFolderDict]
        if "Payload-Folders-Allowed" in self.profile:
            self.allowed = [
                process_allowed_regex_from_profile(x)
                    for x in self.profile["Payload-Folders-Allowed"]
            ]
        else:
            self.allowed = [{"string": r".*", "is_regex": True}]

        self.required: list[PayloadFolderDict] = []
        if "Payload-Folders-Required" in self.profile:
            self.required = [
                {"string": x, "is_regex": False}
                    for x in self.profile["Payload-Folders-Required"]
            ]

        self.bag_path: Optional[Path] = None
        self.log: Optional[Logger] = None

    def get_profile(self) -> NestedDict:
        """Return the profile in self.url (JSON-format) as dictionary."""

        return util.get_profile(self.url)

    def validate_bag(
        self,
        bag_path: str | Path,
        report_back: bool = True
    ) -> int:
        """
        This method executes the validation-logic of the
        PayloadStructureValidator.

        Returns 0 on full conformity and raises a
        PayloadStructureValidationError in case of non-conformity.

        Keyword arguments:
        bag_path -- file path to the bag to be validated either as
                    string literal or pathlib Path
        report_back -- whether or not to print a test result
                       (default True)
        """

        # setup log
        self.log = Logger(default_origin=self.VALIDATOR_TAG)

        # instantiate bag
        if isinstance(bag_path, str):
            self.bag_path = Path(bag_path)
        elif isinstance(bag_path, Path):
            self.bag_path = bag_path
        else:
            raise TypeError(
                "Argument 'bag_path' is expected to be either "
                + "pathlib Path or str. Found " + str(type(bag_path)) + "."
            )

        exitcode = 0

        # use all() to prevent short circuit-evaluation
        # problems are logged with the two validation methods
        if all([self._validate_payload_directories_allowed(),
                self._validate_payload_directories_required(self.bag_path)]):
            self.log.log(
                Context.INFO,
                body=self.POSITIVE_RESPONSE_ALLOW_REQ.format(url=self.url)
            )
        else:
            self.log.log(
                Context.INFO,
                body=self.NEGATIVE_RESPONSE_ALLOW_REQ.format(url=self.url)
            )
            exitcode = 1

        if self._validate_payload_dir_files(self.bag_path):
            self.log.log(
                Context.INFO,
                body=self.POSITIVE_RESPONSE_STRUCT
            )
        else:
            self.log.log(
                Context.INFO,
                body=self.NEGATIVE_RESPONSE_STRUCT
            )
            exitcode = 1

        if self._validate_payload_files_capitalization(self.bag_path):
            self.log.log(
                Context.INFO,
                body=self.POSITIVE_RESPONSE_CAP
            )
        else:
            self.log.log(
                Context.INFO,
                body=self.NEGATIVE_RESPONSE_CAP
            )
            exitcode = 1

        # detailed log on problems
        if report_back:
            print(self.log.fancy(), file=sys.stderr)

        # raise exception if necessary
        if exitcode != 0:
            raise errors.PayloadStructureValidationError(
                "At least one error occurred during validation: "
                + str(self.log).replace("\n", " ")
            )

        return exitcode

    def match_any_regex(
        self,
        path: str,
        patterns: list[PayloadFolderDict],
        use_as_regex_anyway: bool = False
    ) -> bool:
        """
        Returns True if any entry from patterns (dict with boolean
        'is_regex' and str 'string') fully matches with the provided
        path.

        Keyword arguments:
        path -- path to match as string
        patterns -- list of dicts each with the two keys 'is_regex'
                    (boolean) and 'string' (str).
        use_as_regex_anyway -- boolean to determine whether the patterns
                               are checked for 'is_regex' key
                               (default False)
        """

        path = Path(path).as_posix()
        for pattern in patterns:
            if use_as_regex_anyway or pattern["is_regex"]:
                match = re.match(pattern["string"], path)
                if match:
                    return True
            else:
                if Path(pattern["string"]).as_posix() == path:
                    return True
        return False


    def _validate_payload_directories_allowed(self) -> bool:
        """
        Validate the ``Payload-Folders-Allowed`` tag by checking for
        required_but_not_allowed-directories.
        """

        payload_directories_validate = True
        # mypy - hint
        assert self.log is not None

        # for each member of required, ensure it
        # is also in allowed
        required_but_not_allowed = [
            f for f in self.required
              if not self.match_any_regex(f["string"], self.allowed)
        ]
        if required_but_not_allowed:
            payload_directories_validate = False
            for file in required_but_not_allowed:
                required_but_not_allowed_path = file["string"]
                self.log.log(
                    Context.ERROR,
                    body="Required payload directory "
                        + f"'{required_but_not_allowed_path}' not listed in "
                        + "Payload-Folders-Allowed."
                )

        return payload_directories_validate

    def _validate_payload_directories_required(self, bag_path: Path) -> bool:
        """
        Validate the ``Payload-Folders-Required`` tag.

        This validation step checks whether all required directories
        actually exist.

        Keyword arguments:
        bag_path -- pathlib Path to BagIt-Bag that is subject to validation
        """

        payload_directories_validate = True
        # mypy - hint
        assert self.log is not None

        # Payload-directory structure is optional for now, so we return
        # True if none are defined in the profile.
        if "Payload-Folders-Required" not in self.profile:
            return payload_directories_validate

        for payload_dir in self.profile["Payload-Folders-Required"]:
            if not (bag_path / "data" / payload_dir).is_dir():
                payload_directories_validate = False
                self.log.log(
                    Context.ERROR,
                    body=f"Required payload directory '{payload_dir}' is not "
                        + "present in Bag."
                )
        return payload_directories_validate

    def _validate_payload_dir_files(self, bag_path: Path) -> bool:
        """
        Validate that files are only located in directories allowed by
        the payload profile. All relative file paths have to fully match
        their prefix with Payload-Folders-Allowed.

        Keyword arguments:
        bag_path -- pathlib Path to BagIt-Bag that is subject to validation
        """

        # mypy - hint
        assert self.log is not None

        # Payload-directory structure is optional for now, so we return
        # True if none are defined in the profile.
        if "Payload-Folders-Allowed" not in self.profile:
            return True

        # list all files in payload that are allowed
        disallowed_payload_files = util.list_directory_content(
                bag_path / "data",
                pattern="**/*",
                condition_function=lambda p : (
                    p.is_file() \
                    and not self.match_any_regex(
                            str(p.relative_to(bag_path / "data")),
                            self.allowed,
                            use_as_regex_anyway=True
                        )
                )
        )
        # invalid if list is non-empty, list bad files in log
        if disallowed_payload_files:
            for file in disallowed_payload_files:
                relfile = file.relative_to(bag_path)
                self.log.log(
                    Context.ERROR,
                    body=f"File '{relfile}' found in illegal location of "
                        + "payload directory."
                )
            return False
        return True

    def _validate_payload_files_capitalization(self, bag_path: Path) -> bool:
        """
        Validate that files in the payload directory do not differ by
        only their capitalization.

        Keyword arguments:
        bag_path -- pathlib Path to BagIt-Bag that is subject to validation
        """

        payload_file_capitalization_validates = True
        # mypy - hint
        assert self.log is not None

        # list files in payload dir
        payload_files = util.list_directory_content(
                bag_path / "data",
                pattern="**/*",
                condition_function=lambda p : (
                    p.is_file()
                )
        )

        # iterate files and check for multiple occurrences for
        # filename.lower()
        checked: dict[str, str] = {}
        for file in payload_files:
            file_relative = file.relative_to(bag_path)
            file_lower = str(file_relative).lower()
            if file_lower in checked:
                payload_file_capitalization_validates = False
                self.log.log(
                    Context.ERROR,
                    body=f"File '{file_relative}' and '{checked[file_lower]}' "
                        + "only differ in their capitalization."
                )
            else:
                checked[file_lower] = str(file_relative)

        return payload_file_capitalization_validates
