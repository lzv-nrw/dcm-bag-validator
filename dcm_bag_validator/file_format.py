"""
Python module defining the FileFormatValidator-class which
can be used to validate the file formats of a BagIt-Bag's payload
against using a set of plugins specification.

This module has been developed in the LZV.nrw-project. It is structured
in the following way:
 Module          │     Sub-Modules             │
 └ Full Validator│     └ Validator Components  +  File Format Validator-Plugins
                 │                             │

┌─────────────┐  ┌─ ...
│validator.py │  │
│             ├──┤                               ┌──────────────────────┐
│(wrapper)    │  │                            ┌──┤file_format_interface │
└─────────────┘  ├─ ...                       │  ├──────────────────────┤
                 │                            │  │* example.py          │
                 ├─ ...                       │  │                      │
                 │   ┌─────────────────────┐  │  │* veraPDF.py          │
                 ├───┤file_format.py       ├──┘  │                      │
                 │   └─────────────────────┘     │* ...                 │
                 └─ ...                          └──────────────────────┘

Due to the high complexity of file-format validation, the file_format-
validation component itself depends on plugins which are required to
implement the file_format_interface. The instantiation of the
corresponding FileFormatValidator expects a list of plugins. More
specifically, it uses a list of 2-tuples. These contain an instance of
a file_format-plugin as well as information on the the MIME-types that
are to be validated with the corresponding validator-module.
"""

from typing import Optional
import re
import sys
from subprocess import run, CalledProcessError
from pathlib import Path

from dcm_common import util, LoggingContext as Context, Logger

from dcm_bag_validator import errors
from dcm_bag_validator.file_format_plugins.file_format_interface \
    import FileFormatValidatorInterface


class File:
    """
    Record class for File-objects used during the file validation.

    Keyword arguments:
    file_path -- pathlib Path object
    file_type -- string for file's mime type
    """
    def __init__(
        self,
        file_path: Path,
        file_type: Optional[str] = None
    ) -> None:
        self.file_path = file_path
        if file_type is None:
            self.file_type = self.get_mime_type(self.file_path)
        else:
            self.file_type = file_type

    @staticmethod
    def get_mime_type(path: Path) -> Optional[str]:
        """
        Uses fido to determine MIME-type of a file at the given Path path.

        Returns mime-type string or, if not successful, None.

        Keyword arguments:
        path -- pathlib Path to file
        """

        # try to run fido for file type identification
        try:
            fido_result = run(
                ["fido",
                    "-matchprintf",
                    "%(info.mimetype)s"\
                        "\t%(info.matchtype)s"\
                        "\t%(info.signaturename)s\n",
                    str(path)],
                capture_output=True,
                text=True,
                check=True
            )
        except CalledProcessError:
            return None
        # process result
        # depending on file type, fido may return multiple lines
        # for now, simply assume the first is the best match for
        # this purpose
        file_type = \
            fido_result.stdout.split("\n")[0].split("\t")[0].strip()
        return file_type

class FileFormatValidator():
    """
    This class defines the validator for the payload file formats using
    a set of submodules defined at instantiation.

    The constructor expects a list of tuples, where the tuples contain
    pairs of a regex or list of MIME-types and an instance of a
    validator plugin, e.g. [(r"text/.*", some_plugin_object)] or
    [(["text/plain", "image/png"], some_plugin_object)].

    Keyword arguments:
    list_of_validators -- list of tuples, where the tuples contain pairs
                          of a regex or list for accepted MIME-types
                          and an instance of a validator plugin,
                          e.g. [(r"text/.*", some_plugin_object)].
    """

    VALIDATOR_TAG = "File Format Validator"
    VALIDATOR_SUMMARY = \
        "validation of file formats in the payload of BagIt-Bags"
    VALIDATOR_DESCRIPTION = \
        "This validator validates file format conformity of files in the " \
        + "payload of BagIt-Bags based on a set of FileFormatValidatorPlugins."
    POSITIVE_RESPONSE = "\033[32mFile formats are valid.\033[0m"
    NEGATIVE_RESPONSE = "\033[31mFile formats are invalid.\033[0m"

    def __init__(
        self,
        list_of_validators: list[tuple[str | list[str], FileFormatValidatorInterface]]
    ) -> None:
        # make list of validators along with corresponding
        # validator instance
        self.validators: list[tuple[str | list[str], FileFormatValidatorInterface]] \
            = []
        for entry in list_of_validators:
            # check whether input is valid
            if not isinstance(entry[0], list) \
                    and not isinstance(entry[0], str):
                # the accepted file types for a validator plugin need to
                # be either in list- or regex-format
                raise ValueError(
                    "Unknown type selector for file format "\
                    "validator plugin: " \
                    + entry[1].VALIDATOR_TAG + "; " \
                    + str(entry[0])
                )
            else:
                self.validators.append(
                    (entry[0], entry[1])
                )
        self.bag_path: Optional[Path] = None
        self.log: Optional[Logger] = None

    def validate_file(
        self,
        file_path: str | Path | File,
        report_back: bool = True,
        clear_report: bool = True,
        log_summary: bool = True
    ) -> int:
        """
        This method executes the validation-logic of the FileFormatValidator
        acting on a single file.

        Returns 0 on full conformity (1 otherwise) and raises a
        FileFormatValidationError in case of non-conformity.

        Keyword arguments:
        bag_path -- path to the file to be validated either as string,
                    pathlib Path, or file_format.File-object
        report_back -- whether or not to print a test result
                       (default True)
        clear_report -- whether or not start with a clean report
                        (default True)
        log_summary -- whether or not to print overall result to log
                       (default True)
        """

        # setup log
        if clear_report:
            self.log = Logger(default_origin=self.VALIDATOR_TAG)

        # convert input type
        _file_path = util.make_path(file_path)
        if isinstance(file_path, Path):
            file = File(file_path=_file_path)

        exitcode = 0

        if file.file_type is None:
            # mark validation as failed
            exitcode = 1
            # write message for log
            self.log.log(
                Context.ERROR,
                body=f"Unable to analyze file '{str(file.file_path)}' using fido."
            )
            return exitcode

        # iterate validators to check for conformity
        for validator_tuple in self.validators:
            # check if this file type is to be tested with given
            # validator plugin validator_tuple[1]
            if isinstance(validator_tuple[0], list):
                # test whether type in list of types for validator
                if file.file_type not in validator_tuple[0]:
                    # issue warning for left out file
                    self.log.log(
                        Context.WARNING,
                        origin=validator_tuple[1].VALIDATOR_TAG,
                        body=f"File '{str(file.file_path)}' is left unchecked;"
                            + f" no match for '{file.file_type}' in "
                            + f"list of types '{str(validator_tuple[0])}'"
                    )
                    continue
            elif isinstance(validator_tuple[0], str):
                # test regex
                if not re.fullmatch(validator_tuple[0], file.file_type):
                    # issue warning for left out file
                    self.log.log(
                        Context.WARNING,
                        origin=validator_tuple[1].VALIDATOR_TAG,
                        body=f"File '{str(file.file_path)}' is left unchecked;"
                            + f" no match for '{file.file_type}' in "
                            + f"file type regex '{str(validator_tuple[0])}'"
                    )
                    continue
            else:
                raise ValueError(
                    "Unknown type selector for file format "
                    + "validator plugin: "
                    + validator_tuple[1].VALIDATOR_TAG + "; "
                    + str(validator_tuple[0])
                )

            # execute validation
            this_exit_code = validator_tuple[1].validate_file_format(
                file.file_path,
                file.file_type
            )

            # copy report
            self.log.merge(validator_tuple[1].log)

            # apply result
            if this_exit_code != 0:
                exitcode = 1

        self._finalize(exitcode, report_back, log_summary)

        return exitcode

    def validate_bag(
        self,
        bag_path: str | Path,
        report_back: bool = True
    ) -> int:
        """
        This method executes the validation-logic of the FileFormatValidator.

        Returns 0 on full conformity and raises a FileFormatValidationError
        in case of non-conformity.

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
                "pathlib Path or str. Found " + str(type(bag_path)) + "."
            )

        exitcode = 0

        # list files in payload directory
        if not isinstance(bag_path, Path):
            bag_path = Path(bag_path)
        files = util.list_directory_content(
            (bag_path / "data"),
            pattern="**/*",
            condition_function=lambda p : p.is_file()
        )

        # iterate files to check for conformity
        for file in files:
            try:
                this_exit_code = self.validate_file(
                    file,
                    report_back=False,
                    clear_report=False,
                    log_summary=False
                )
            except errors.FileFormatValidationError:
                this_exit_code = 1

            # apply result
            if this_exit_code != 0:
                exitcode = 1

        self._finalize(exitcode, report_back, True)

        return exitcode

    def _finalize(
        self,
        exitcode: int,
        report_back: bool,
        print_log: bool
    ) -> None:
        if print_log:
            if exitcode == 0:
                self.log.log(
                    Context.INFO,
                    body=self.POSITIVE_RESPONSE
                )
            else:
                self.log.log(
                    Context.INFO,
                    body=self.NEGATIVE_RESPONSE
                )

        # detailed report on problems
        if report_back:
            if self.log:
                print(self.log.fancy(), file=sys.stderr)

        # raise exception if necessary
        if exitcode != 0:
            raise errors.FileFormatValidationError(
                "At least one error occurred during file format validation: "
                + str(self.log).replace("\n", " ")
            )
