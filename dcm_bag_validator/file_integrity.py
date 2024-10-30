"""
Python module defining the PayloadIntegrityValidator-class which
can be used to validate a BagIt-Bag's payload integrity.

This module has been developed in the LZV.nrw-project.
"""

from typing import Optional
from pathlib import Path
import hashlib

from dcm_common import LoggingContext as Context, Logger

from dcm_bag_validator import errors


SUPPORTED_HASHING_METHODS = {
    "md5": hashlib.md5,
    "sha1": hashlib.sha1,
    "sha256": hashlib.sha256,
    "sha512": hashlib.sha512
}


def hash_from_bytes(
    method_id: str,
    data: bytes
) -> str:
    """
    Returns the hash of data as string resulting from some method.

    The method-information has to be given as a string-identifier (see
    definition of `SUPPORTED_HASHING_METHODS`).

    Keyword arguments:
    method_id -- string identifier for hashing method
                 (see definition of `SUPPORTED_HASHING_METHODS`)
    data -- byte-encoded string
    """

    if method_id not in SUPPORTED_HASHING_METHODS:
        raise ValueError(
            f"Unknown method '{method_id}' " \
                f"(available: {str(SUPPORTED_HASHING_METHODS.keys())})."
        )

    return SUPPORTED_HASHING_METHODS[method_id](data).hexdigest()


def hash_from_file(
    method_id: str,
    path: Path
) -> str:
    """
    Returns the file hash as string resulting from some method.

    The method-information has to be given as a string-identifier (see
    definition of `SUPPORTED_HASHING_METHODS`).

    Keyword arguments:
    method_id -- string identifier for hashing method
                 (see definition of `SUPPORTED_HASHING_METHODS`)
    path -- file intended for hashing
    """

    return hash_from_bytes(method_id, path.read_bytes())


class FileIntegrityValidator:
    """
    Validates file checksums.

    Keyword arguments:
    method -- string identifier of a hashing method (see
              `SUPPORTED_HASHING_METHODS` for available options)
    value -- expected hash value
    """

    VALIDATOR_TAG = "Object Checksum Validator"
    VALIDATOR_SUMMARY = "validation of file checksums"
    VALIDATOR_DESCRIPTION = \
        "This validator validates a file's checksum against some value."
    POSITIVE_RESPONSE = "\033[32mChecksum is valid.\033[0m"
    NEGATIVE_RESPONSE = "\033[31mChecksum is invalid.\033[0m"
    ERROR_DETAIL_RESPONSE = \
        "Validation failed. (Expected '{}', but found '{}'.)"

    def __init__(
        self, method: Optional[str] = None, value: Optional[str] = None
    ) -> None:
        self.method = None
        self.method = self._get_method(method, True)
        self.value = value
        self.log: Optional[Logger] = None

    def _get_method(self, method, accept_none: bool = False) -> str:
        if not accept_none and method is None and self.method is None:
            raise ValueError("Missing required argument 'method'.")

        if method is not None and method not in SUPPORTED_HASHING_METHODS:
            raise ValueError(
                f"Value '{method}' for 'method' not allowed. "
                    + f"Supported values: {SUPPORTED_HASHING_METHODS}."
            )

        return method or self.method

    def validate_file(
        self,
        file_path: str | Path,
        report_back: bool = False,
        method: Optional[str] = None,
        value: Optional[str] = None
    ) -> int:
        """
        Returns 0 if file is valid and raises `PayloadIntegrityValidationError`
        otherwise.

        Keyword arguments:
        file_path -- path to the target file
        report_back -- if `True`, print resulting log into stdout
        method -- string identifier of a hashing method (see
                  `SUPPORTED_HASHING_METHODS` for available options)
                  (default None; uses self.method)
        value -- expected hash value
                 (default None; uses self.value)
        """

        self.log = Logger(default_origin=self.VALIDATOR_TAG)

        _method = self._get_method(method, False)
        _value = value or self.value
        if _value is None:
            raise ValueError("Missing required argument 'value'.")

        _hashed = hash_from_file(
            _method,
            file_path
        )
        if _hashed == _value:
            self.log.log(
                Context.INFO,
                body=self.POSITIVE_RESPONSE
            )
        else:
            self.log.log(
                Context.INFO,
                body=self.NEGATIVE_RESPONSE
            )
            self.log.log(
                Context.ERROR,
                body=self.ERROR_DETAIL_RESPONSE.format(_value, _hashed)
            )

        if report_back:
            print(self.log.fancy())

        if Context.ERROR in self.log:
            raise errors.PayloadIntegrityValidationError("Invalid file.")
        return 0
