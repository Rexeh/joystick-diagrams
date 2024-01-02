from pathlib import Path
from unittest.mock import patch

from joystick_diagrams.functions import helper


def test_dir_create_exception(caplog):
    with patch.object(Path, "mkdir") as mock_mkdir:
        mock_mkdir.side_effect = OSError
        helper.create_directory("testdir")

        assert "Failed to create directory: testdir" in caplog.text
