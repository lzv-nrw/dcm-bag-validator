"""
This module contains a set of specific types of exceptions for the
validation of Bags.
"""

class ValidationError(Exception):
    """General error during validation."""
    pass

class SerializationValidationError(ValidationError):
    """Error during validation of bag serialization."""
    pass

class ProfileValidationError(ValidationError):
    """Error during validation of profile-related properties."""
    pass

class PayloadStructureValidationError(ValidationError):
    """Error during validation of payload directory-structure."""
    pass

class PayloadIntegrityValidationError(ValidationError):
    """Error during validation of payload integrity."""
    pass

class FileFormatValidationError(ValidationError):
    """Error during validation of file format."""
    pass