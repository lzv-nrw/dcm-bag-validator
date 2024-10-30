"""
File format depth validator plugin using Jhove.
https://jhove.openpreservation.org/

script idea based on jhove implementation in goobi
https://github.com/akademy/goobi.scripts/blob/master/jhove/jhove.py
"""

from typing import TypedDict, Optional
from pathlib import Path
import os
from subprocess import run, CalledProcessError
import json
import itertools

from xmltodict import parse as xml_parse
from dcm_common import LoggingContext as Context, Logger

from dcm_bag_validator.file_format_plugins import file_format_interface


class JhoveResponseDict(TypedDict):
    info: list[str]
    error: list[str]


class JhovePlugin(
    file_format_interface.FileFormatValidatorInterface
):
    """
    File format validator plugin class based on the jhove application
    for validation of file formats. Objects of this class can be used in
    the file format validator module in the dcm_bag_validator package.

    Keyword arguments:
    jhove_app -- path to the jhove command line starter script; this can
                 also be set using the 'JHOVE_APP' environment variable
                 (default None)
    jhove_conf_path -- path to the jhove configuration file; this can be
                       also be set using the 'JHOVE_APP_CONF' environment
                       variable
                       (default None)
    """

    log = Logger()

    # see https://jhove.openpreservation.org/modules/
    # the text/plain-related modules UTF8-hul and ASCII-hul are dropped
    # because fido does not report charset
    FILETYPE_MODULES = {
        "": ["text/plain"],  # this makes jhove choose module by itself
        "AIFF-hul":  ["audio/x-aiff"],
        "GIF-hul":  ["image/gif"],
        "HTML-hul":  ["text/html"],
        "JPEG-hul":  ["image/jpeg"],
        "JPEG2000-hul":  ["image/jp2", "image/jpx"],
        "PDF-hul":  ["application/pdf"],
        "TIFF-hul":  ["image/tiff", "image/tiff-fx", "image/ief"],
        "WAVE-hul":  ["audio/vnd.wave"],
        "XML-hul":  ["text/xml"],
        "PNG-gdm":  ["image/png"],  # third party
    }
    DEFAULT_FILE_FORMATS = list(
        itertools.chain(
            *FILETYPE_MODULES.values()
        )
    )
    VALIDATOR_TAG = "JHOVE-Plugin"
    VALIDATOR_SUMMARY = "file format validation based on JHOVE"
    VALIDATOR_DESCRIPTION = \
        "This plugin uses the JHOVE software by the Open Preservation " \
        + "Foundation to validate file formats: " \
        + "https://jhove.openpreservation.org/ " \
        + "It is configured with the following module-map:" \
        + "; ".join(
            f"{key}: {str(value)}" for key, value in FILETYPE_MODULES.items()
        )

    def __init__(
        self,
        jhove_app: Optional[Path] = None,
        jhove_conf_path: Optional[Path] = None
    ) -> None:
        self.jhove: str | Path = ""
        if not jhove_app:
            self.jhove = os.environ.get("JHOVE_APP") or "jhove"
        else:
            self.jhove = jhove_app
        self.jhove_conf_path: Optional[str | Path] = None
        if not jhove_conf_path:
            self.jhove_conf_path = os.environ.get("JHOVE_APP_CONF")
        else:
            self.jhove_conf_path = jhove_conf_path

    def _find_key_for_value(self, search_value: str) -> str | None:
        """
        Extract key corresponding to given value in FILETYPE_MODULES-dict.
        """
        for key, values in self.FILETYPE_MODULES.items():
            if any(search_value.lower() in value for value in values):
                return key
        return None

    def validate_file_format(self, file_path: Path, file_type: str) -> int:
        self.log = Logger(default_origin=self.VALIDATOR_TAG)
        key = self._find_key_for_value(file_type)
        if key is None:
            self.log.log(
                Context.ERROR,
                body=f"File '{str(file_path)}' unchecked by jhove, "
                    + f"no suitable module found for {file_type}."
            )
            return 1

        result = self._check_file(
            file_path, key
        )

        # add info-messages to log
        for message in result["info"]:
            self.log.log(
                Context.INFO,
                body=message
            )
        # done if no error-messages
        if len(result["error"]) == 0:
            self.log.log(
                Context.INFO,
                body=f"File '{str(file_path)}' is well-formed."
            )
            return 0
        # otherwise also add errors to log
        for message in result["error"]:
            self.log.log(
                Context.ERROR,
                body=message
            )
        return 1

    def _check_file(
        self,
        file_path: str | Path,
        module: str
    ) -> JhoveResponseDict:
        """Execute call to jhove."""

        command = self._default_command()
        if module != "":
            command.extend(["-m", module])

        # in some cases, (e.g. for the PNG-gdm module) jhove has been
        # found to crash when using the JSON-schema but not the XML-schema
        # -> try JSON first and if not successful try also XML
        result = self._call_json(
            command, file_path
        )
        if result is None:
            result = self._call_xml(
                command, file_path
            )
        if result is None:
            return {
                "info": [],
                "error": [
                    self.VALIDATOR_TAG
                        + f": File '{str(file_path)}', unable to invoke jhove"
                        + f" with module '{module}'."
                ]
            }

        return result

    def _call_xml(
        self, command: list[str], file_path: str | Path
    ) -> Optional[JhoveResponseDict]:
        """
        Make call to jhove using XML output format and process result.
        """
        try:
            jhove_returned = xml_parse(
                run(
                    command + ["-h", "XML", str(file_path)],
                    capture_output=True,
                    text=True,
                    check=True
                ).stdout
            )
        except CalledProcessError:
            return None
        result: JhoveResponseDict = {"info": [], "error": []}
        if "jhove" in jhove_returned \
                and isinstance(jhove_returned["jhove"], dict) \
                and "repInfo" in jhove_returned["jhove"]:
            if isinstance(jhove_returned["jhove"]["repInfo"], dict) \
                    and "messages" in jhove_returned["jhove"]["repInfo"] \
                    and isinstance(jhove_returned["jhove"]["repInfo"]["messages"], dict) \
                    and "message" in jhove_returned["jhove"]["repInfo"]["messages"]:
                if isinstance(
                    jhove_returned["jhove"]["repInfo"]["messages"]["message"], list
                ):
                    messages = jhove_returned["jhove"]["repInfo"]["messages"]["message"]
                else:
                    messages = [jhove_returned["jhove"]["repInfo"]["messages"]["message"]]
                for message in messages:
                    if "@severity" in message:
                        target = "error"
                        if message["@severity"] == "info":
                            target = "info"
                        _message = message["#text"]
                        if "@id" in message:
                            _message = _message \
                                + f" ({message['@id']})"
                        result[target].append(_message)  # type: ignore[literal-required]
            else:
                # no errors
                pass
        else:
            return {
                "info": [],
                "error": [
                    self.VALIDATOR_TAG
                    + f": File '{str(file_path)}', jhove gave bad response."
                ]
            }
        return result

    def _call_json(
        self, command: list[str], file_path: str | Path
    ) -> Optional[JhoveResponseDict]:
        """
        Make call to jhove using JSON output format and process result.
        """
        try:
            jhove_returned = json.loads(
                run(
                    command + ["-h", "JSON", str(file_path)],
                    capture_output=True,
                    text=True,
                    check=True
                ).stdout
            )
        except CalledProcessError:
            return None
        result: JhoveResponseDict = {"info": [], "error": []}
        if "jhove" in jhove_returned \
                and isinstance(jhove_returned["jhove"], dict) \
                and "repInfo" in jhove_returned["jhove"] \
                and isinstance(jhove_returned["jhove"]["repInfo"], list) \
                and len(jhove_returned["jhove"]["repInfo"]) > 0:
            if "messages" in jhove_returned["jhove"]["repInfo"][0]:
                for message in \
                        jhove_returned["jhove"]["repInfo"][0]["messages"]:
                    if "severity" in message:
                        target = "error"
                        if message["severity"] == "info":
                            target = "info"
                        _message = message["message"]
                        if "id" in message:
                            _message = _message + f" ({message['id']})"
                        result[target].append(_message)  # type: ignore[literal-required]
            else:
                # no errors
                pass
        else:
            return {
                "info": [],
                "error": [
                    self.VALIDATOR_TAG
                    + f": File '{str(file_path)}', jhove gave bad response."
                ]
            }
        return result

    def _default_command(self) -> list[str]:
        if self.jhove_conf_path:
            command = [str(self.jhove), "-l OFF", "-e utf8",
                    "-c", str(self.jhove_conf_path)]
        else:
            command = [str(self.jhove), "-l OFF", "-e utf8"]
        return command
