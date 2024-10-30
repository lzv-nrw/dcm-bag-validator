"""
This module contains an interface for the
definition of a file format-validator plugin.
"""

from pathlib import Path
import abc


class FileFormatValidatorInterface(metaclass=abc.ABCMeta):
    """
    Interface for the definition of FileFormatValidator-plugins.

    Requirements to qualify as FileFormatValidatorPlugin:
    log -- property (Logger); BasicLogger object
    VALIDATOR_TAG -- property (str); plugin's tag
    VALIDATOR_SUMMARY -- property (str); short description of plugin
    VALIDATOR_DESCRIPTION -- property (str); long description of plugin
    DEFAULT_FILE_FORMATS -- property (str|list[str]); regex/list of
                            mime-types for accepted file formats that
                            can be used as default
    validate_file_format -- method (int); validation method for files
    """

    @classmethod
    def __subclasshook__(cls, subclass):
        return (
            hasattr(subclass, "log")
            and hasattr(subclass, "VALIDATOR_TAG")
            and hasattr(subclass, "VALIDATOR_SUMMARY")
            and hasattr(subclass, "VALIDATOR_DESCRIPTION")
            and hasattr(subclass, "DEFAULT_FILE_FORMATS")
            and hasattr(subclass, "validate_file_format")
            and callable(subclass.validate_file_format)
            or NotImplemented
        )

    @property
    @abc.abstractmethod
    def log(self):
        raise NotImplementedError(
            f"Class {self.__class__.__name__} does not define self.log."
        )

    @property
    @abc.abstractmethod
    def VALIDATOR_TAG(self):
        raise NotImplementedError(
            f"Class {self.__class__.__name__} does not define "
            + "self.VALIDATOR_TAG."
        )

    @property
    @abc.abstractmethod
    def VALIDATOR_SUMMARY(self):
        raise NotImplementedError(
            f"Class {self.__class__.__name__} does not define "
            + "self.VALIDATOR_SUMMARY."
        )

    @property
    @abc.abstractmethod
    def VALIDATOR_DESCRIPTION(self):
        raise NotImplementedError(
            f"Class {self.__class__.__name__} does not define "
            + "self.VALIDATOR_DESCRIPTION."
        )

    @property
    @abc.abstractmethod
    def DEFAULT_FILE_FORMATS(self):
        raise NotImplementedError(
            f"Class {self.__class__.__name__} does not define "
            + "self.DEFAULT_FILE_FORMATS."
        )

    @abc.abstractmethod
    def validate_file_format(self, file_path: Path, file_type: str) -> int:
        """Validate a file at file_path against its file_type."""
        raise NotImplementedError(
            f"Class {self.__class__.__name__} does not define "
            + "self.validate_file_format."
        )
