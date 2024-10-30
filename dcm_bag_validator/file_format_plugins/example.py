"""
File format validator plugin to demonstrate plugin-implementation.
"""

from pathlib import Path

from dcm_common import LoggingContext as Context, Logger

from dcm_bag_validator.file_format_plugins import file_format_interface


class ExamplePlugin(
    file_format_interface.FileFormatValidatorInterface
):
    """
    Example plugin demonstrating the basic usage of the
    FileFormatValidatorInterface.
    """

    VALIDATOR_TAG = "File Extension Validator"
    VALIDATOR_SUMMARY = "File format validation plugin-template"
    VALIDATOR_DESCRIPTION = \
        "This plugin demonstrates the definition of file format validation " \
        + "plugins by implementing a file validation based on file extension."\
        + " It is not intended to be used for production."
    log = Logger(default_origin=VALIDATOR_TAG)

    # see http://svn.apache.org/viewvc/httpd/httpd/trunk/docs/conf/mime.types?view=markup
    MIME_TYPE_EXTENSION_MAP = {
        "text/csv": ["csv"],
        "text/html":["html", "htm"],
        "text/plain": ["txt", "text", "conf", "def", "list", "log", "in"],
        "image/bmp": ["bmp"],
        "image/gif": ["gif"],
        "image/tiff": ["tiff", "tif"],
        "image/png": ["png"],
        "image/jpeg": ["jpeg", "jpg", "jpe"],
        "video/webm": ["webm"],
        "video/x-matroska": ["mkv", "mk3d", "mks"]
    }
    DEFAULT_FILE_FORMATS = list(MIME_TYPE_EXTENSION_MAP.keys())

    def validate_file_format(self, file_path: Path, file_type: str) -> int:
        """Validate a file at file_path against its format."""

        # renew log for every file
        self.log = Logger(default_origin=self.VALIDATOR_TAG)

        # do something clever
        # ...
        if file_type in self.MIME_TYPE_EXTENSION_MAP:
            is_plausible = \
                file_path.suffix.lower().strip(".") \
                    in self.MIME_TYPE_EXTENSION_MAP[file_type]
        else:
            # debatable..
            # format validator plugin does not see anything wrong
            is_plausible = True

        # return verdict
        if is_plausible:
            return 0
        self.log.log(
            Context.ERROR,
            body=f"'{str(file_path)}' has unknown type or invalid extension."
        )
        return 1
