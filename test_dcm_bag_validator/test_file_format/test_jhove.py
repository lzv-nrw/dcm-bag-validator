"""
This module contains pytest-tests for testing the jhove plugin for the
file_format validator.
"""

from unittest import mock
from pathlib import Path
from typing import Optional
from subprocess import CalledProcessError

import pytest
from dcm_common import LoggingContext as Context

from dcm_bag_validator.file_format_plugins \
    import jhove


@pytest.fixture(name="subprocess_patcher_factory")
def _subprocess_patcher_factory():
    """
    Returns factory for generating patchers for fake
    subprocess.run with stdout return value from given argument.
    """
    def subprocess_patcher(stdout: str, accepted_format: Optional[str] = None):
        """Returns patcher for fake subprocess.run"""
        def faked_run(*args, **kwargs):
            if accepted_format is not None and accepted_format not in args[0]:
                raise CalledProcessError(1, "")
            class Response:
                def __init__(self, _stdout):
                    self.stdout = _stdout
            return Response(stdout)
        return mock.patch(
            "dcm_bag_validator.file_format_plugins.jhove.run",
            side_effect=faked_run
        )
    return subprocess_patcher


@pytest.fixture(name="fake_module")
def _fake_module():
    return "module-id"


@pytest.fixture(name="fake_message")
def _fake_message():
    return "Error message"


@pytest.fixture(name="response_good_json")
def _response_good_json(fake_module):
    return """{"jhove":
  {"repInfo": [{"module": """ + f'"{fake_module}"' + """}]}
}
"""


@pytest.fixture(name="response_bad_json")
def _response_bad_json(fake_module, fake_message):
    return """{"jhove":
  {"repInfo": [
    {"messages": [
        {"message": """ + f'"{fake_message}"' + """, "severity": "error", "id": """ + f'"{fake_module}"' + """}
    ]}
  ]}
}
"""


@pytest.fixture(name="response_good_xml")
def _response_good_xml(fake_module):
    return """<?xml version="1.0" encoding="UTF-8"?>
<jhove>
  <repInfo>
    <module>""" + f"{fake_module}" + """</module>
  </repInfo>
</jhove>
"""


@pytest.fixture(name="response_bad_xml")
def _response_bad_xml(fake_module, fake_message):
    return """<?xml version="1.0" encoding="UTF-8"?>
<jhove>
  <repInfo>
    <messages>
      <message severity="error" id=""" + f'"{fake_module}"' + """>""" + f"{fake_message}" + """</message>
    </messages>
  </repInfo>
</jhove>
"""


@pytest.mark.parametrize(
    ("response", "accepted_format", "expected_result"),
    [
        ("response_good_json", None, 0),
        ("response_bad_json", None, 1),
        ("response_good_xml", "XML", 0),
        ("response_bad_xml", "XML", 1)
    ],
    ids=["good_json", "bad_json", "good_xml", "bad_xml"]
)
def test_validate_file_format_basic(
    response, accepted_format, expected_result,
    subprocess_patcher_factory, fake_module, fake_message,
    request
):
    """
    Test method validate_file_format of JhovePlugin by faking subprocess call.

    A patcher is used to mimic the required behavior of `subprocess.run`
    (see fixture `subprocess_patcher_factory` for details).
    """

    # get value from fixture
    _response = request.getfixturevalue(response)
    # get patcher for faked subprocess call
    patcher = subprocess_patcher_factory(
        _response, accepted_format=accepted_format
    )

    # make validator object
    validator = jhove.JhovePlugin()

    # make fake call
    patcher.start()
    exit_code = validator.validate_file_format(Path(""), "image/tiff")
    patcher.stop()

    assert exit_code == expected_result

    if expected_result == 1:
        errors = validator.log[Context.ERROR]
        assert len(errors) == 1
        assert fake_module in errors[0].body
        assert fake_message in errors[0].body


@pytest.mark.parametrize(
    ("response", "accepted_format", "expected_result"),
    [
        ('{"no-jhove": {}}', None, 1),
        ('{"jhove": 2}', None, 1),
        ('{"jhove": {}}', None, 1),
        ('{"jhove": {"repInfo": 0}}', None, 1),
        ('{"jhove": {"repInfo": []}}', None, 1),
        ('<?xml version="1.0" encoding="UTF-8"?><no-jhove></no-jhove>', "XML", 1),
        ('<?xml version="1.0" encoding="UTF-8"?><jhove><no-repInfo></no-repInfo></jhove>', "XML", 1),
    ],
    ids=["json-0", "json-1", "json-2", "json-3", "json-4", "xml-0", "xml-1"]
)
def test_validate_file_format_bad_response_format(
    response, accepted_format, expected_result,
    subprocess_patcher_factory
):
    """
    Test method validate_file_format of JhovePlugin for bad response
    format.
    """

    # get patcher for faked subprocess call
    patcher = subprocess_patcher_factory(
        response, accepted_format=accepted_format
    )

    # make validator object
    validator = jhove.JhovePlugin()

    # make fake call
    patcher.start()
    exit_code = validator.validate_file_format(Path(""), "image/tiff")
    patcher.stop()

    assert exit_code == expected_result


def test_validate_file_format_unknown_type():
    """
    Test method validate_file_format of JhovePlugin for mime type that
    has no corresponding module.
    """

    # make validator object
    validator = jhove.JhovePlugin()
    # make call
    exit_code = validator.validate_file_format(Path(""), "image/unknown")

    assert exit_code == 1
    assert len(
        validator.log[Context.ERROR]
    ) == 1


@pytest.mark.parametrize(
    ("response", "accepted_format"),
    [
        ("""{"jhove":
  {"repInfo": [
    {"messages": [
        {"message": "message 0", "severity": "error", "id": "module-id"},
        {"message": "message 1", "severity": "error", "id": "module-id"}
    ]}
  ]}
}
""", None),
    ("""<?xml version="1.0" encoding="UTF-8"?>
<jhove>
  <repInfo>
    <messages>
      <message severity="error" id="module-id">message 0</message>
      <message severity="error" id="module-id">message 1</message>
    </messages>
  </repInfo>
</jhove>
""", "XML"),
    ],
    ids=["json", "xml"]
)
def test_validate_file_format_multiple_messages(
    response, accepted_format, subprocess_patcher_factory
):
    """
    Test method validate_file_format of JhovePlugin for multiple
    messages in response.
    """

    # get patcher for faked subprocess call
    patcher = subprocess_patcher_factory(
        response, accepted_format=accepted_format
    )

    # make validator object
    validator = jhove.JhovePlugin()

    # make fake call
    patcher.start()
    exit_code = validator.validate_file_format(Path(""), "image/tiff")
    patcher.stop()

    assert exit_code == 1

    errors = validator.log[Context.ERROR]
    assert len(errors) == 2
    for i, msg in enumerate(errors):
        assert f"message {i}" in msg.body


@pytest.mark.parametrize(
    ("response", "accepted_format"),
    [
        ("""{"jhove":
  {"repInfo": [
    {"messages": [
        {"message": "message info", "severity": "info", "id": "module-id"},
        {"message": "message error", "severity": "error", "id": "module-id"}
    ]}
  ]}
}
""", None),
    ("""<?xml version="1.0" encoding="UTF-8"?>
<jhove>
  <repInfo>
    <messages>
      <message severity="info" id="module-id">message info</message>
      <message severity="error" id="module-id">message error</message>
    </messages>
  </repInfo>
</jhove>
""", "XML"),
    ],
    ids=["json", "xml"]
)
def test_validate_file_format_multiple_message_types(
    response, accepted_format, subprocess_patcher_factory
):
    """
    Test method validate_file_format of JhovePlugin for multiple
    message types in response.
    """

    # get patcher for faked subprocess call
    patcher = subprocess_patcher_factory(
        response, accepted_format=accepted_format
    )

    # make validator object
    validator = jhove.JhovePlugin()

    # make fake call
    patcher.start()
    exit_code = validator.validate_file_format(Path(""), "image/tiff")
    patcher.stop()

    assert exit_code == 1

    errors = validator.log[Context.ERROR]
    info = validator.log[Context.INFO]
    assert len(errors) == 1
    assert len(info) == 1
    assert "message error" in errors[0].body
    assert "message info" in info[0].body


def test_validate_file_format_failed(subprocess_patcher_factory):
    """
    Test method validate_file_format of JhovePlugin when all output
    formats cause error.
    """

    # get patcher for faked subprocess call
    patcher = subprocess_patcher_factory(
        "", accepted_format="UNKNOWN_FORMAT"
    )

    # make validator object
    validator = jhove.JhovePlugin()

    # make fake call
    patcher.start()
    exit_code = validator.validate_file_format(Path(""), "image/tiff")
    patcher.stop()

    assert exit_code == 1
