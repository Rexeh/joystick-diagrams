"""Shared fixtures for the UI test suite.

Several UI tests reach the database for real: building an ``AppState`` constructs a
``LabelService`` that reads ``bind_text`` on init, and the install flow reads the
``plugins`` configuration table to decide whether a plugin is new. Both need a schema
that exists, and neither should touch the developer's real database.
"""

import os
from unittest.mock import patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from joystick_diagrams.db import db_handler  # noqa: E402


@pytest.fixture(autouse=True)
def temp_database(tmp_path):
    """Give every UI test a throwaway data root with a fully migrated schema.

    Without this the suite fails on any machine (or CI runner) that has never run the
    app — the tables simply do not exist.

    ``db_connection`` binds ``data_root`` at import time (``from ... import
    data_root``), so patching ``joystick_diagrams.utils.data_root`` alone does **not**
    reach it. The binding inside ``db_connection`` is the one that decides where the
    sqlite file lives; ``db_handler.init`` reaches ``data_root`` through the ``utils``
    module, so both are redirected.
    """
    root = tmp_path / "data_root"
    root.mkdir()
    with (
        patch("joystick_diagrams.db.db_connection.data_root", return_value=root),
        patch("joystick_diagrams.utils.data_root", return_value=root),
    ):
        db_handler.init()
        yield
