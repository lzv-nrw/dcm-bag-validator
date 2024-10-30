import re

import pytest


@pytest.fixture(name="pattern_in_list_of_strings")
def _pattern_in_list_of_strings():
    def pattern_in_list_of_strings(pattern: str, list_of_strings: list[str]) \
            -> tuple[bool, int]:
        """
        Iterate over a list of strings and count occurrences of pattern.
        """

        occurrences = 0

        for _msg in list_of_strings:
            if re.match(pattern, _msg) is not None:
                occurrences = occurrences + 1
        return occurrences > 0, occurrences
    return pattern_in_list_of_strings
