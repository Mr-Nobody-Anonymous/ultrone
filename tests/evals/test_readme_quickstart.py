"""Verifies that the documented README entrypoint functions cleanly."""

import pytest
from apps.api.main import main


def test_readme_quickstart():
    # Calling root entrypoint with help flag should exit cleanly (SystemExit with code 0)
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    assert excinfo.value.code == 0
