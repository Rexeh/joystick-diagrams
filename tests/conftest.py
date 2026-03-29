from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_db_get_setting():
    with patch("joystick_diagrams.db.db_settings.get_setting", return_value=None):
        yield
