"""Tests for the OpenKneeboard output plugin.

The plugin is designed to feed PNG kneeboard pages into DCS / OpenKneeboard.
SVG results must be skipped even if they happen to be in the same batch —
OpenKneeboard cannot render raw SVGs.
"""

from pathlib import Path

import pytest

from joystick_diagrams.input.device import Device_
from joystick_diagrams.plugins.output_plugin_interface import ExportResult
from joystick_diagrams.plugins.output_plugins.openkneeboard.main import (
    DCS_KNEEBOARD,
    FOLDER_TAB,
    OutputPlugin,
)

GUID = "aaaa0000-0000-0000-0000-000000000001"


def _result(file_path: Path, export_format: str, profile_name: str = "A-10C II"):
    return ExportResult(
        profile_name=profile_name,
        device_name="Test Device",
        device_guid=GUID,
        source_plugin="DCS World",
        template_name=None,
        export_format=export_format,
        file_path=file_path,
        export_directory=file_path.parent,
        device=Device_(GUID, "Test Device"),
    )


@pytest.fixture
def plugin_dcs(tmp_path, monkeypatch):
    """OpenKneeboard plugin configured for DCS mode, pointing at tmp_path."""
    # Isolate plugin data path so saves don't hit real user directories.
    monkeypatch.setattr(
        "joystick_diagrams.utils.plugin_data_root",
        lambda: tmp_path / "plugin_data",
    )
    plugin = OutputPlugin()
    plugin.update_setting("mode", DCS_KNEEBOARD)
    plugin.update_setting("saved_games_path", tmp_path / "saved_games")
    plugin.update_setting("organize_by_profile", False)
    plugin.update_setting("use_subfolder", False)
    return plugin


@pytest.fixture
def plugin_folder(tmp_path, monkeypatch):
    """OpenKneeboard plugin configured for Folder Tab mode."""
    monkeypatch.setattr(
        "joystick_diagrams.utils.plugin_data_root",
        lambda: tmp_path / "plugin_data",
    )
    plugin = OutputPlugin()
    plugin.update_setting("mode", FOLDER_TAB)
    plugin.update_setting("output_folder", tmp_path / "out")
    plugin.update_setting("organize_by_profile", False)
    plugin.update_setting("use_subfolder", False)
    return plugin


class TestProcessExportFiltersByFormat:
    def test_dcs_mode_skips_svg_copies_only_png(self, plugin_dcs, tmp_path):
        png_file = tmp_path / "warthog.png"
        png_file.write_bytes(b"png-bytes")
        svg_file = tmp_path / "warthog.svg"
        svg_file.write_text("<svg/>")

        results = [
            _result(svg_file, "SVG"),
            _result(png_file, "PNG"),
        ]

        assert plugin_dcs.process_export(results) is True

        dest_dir = tmp_path / "saved_games" / "KNEEBOARD"
        assert (dest_dir / "warthog.png").exists()
        assert not (dest_dir / "warthog.svg").exists()

    def test_dcs_mode_all_svg_is_noop_and_returns_true(self, plugin_dcs, tmp_path):
        """A batch of only-SVG results should not error and should not
        create anything in the kneeboard folder."""
        svg_file = tmp_path / "warthog.svg"
        svg_file.write_text("<svg/>")

        results = [_result(svg_file, "SVG")]

        assert plugin_dcs.process_export(results) is True
        assert not (tmp_path / "saved_games" / "KNEEBOARD" / "warthog.svg").exists()

    def test_folder_mode_skips_svg_copies_only_png(self, plugin_folder, tmp_path):
        png_file = tmp_path / "warthog.png"
        png_file.write_bytes(b"png-bytes")
        svg_file = tmp_path / "warthog.svg"
        svg_file.write_text("<svg/>")

        results = [
            _result(svg_file, "SVG"),
            _result(png_file, "PNG"),
        ]

        assert plugin_folder.process_export(results) is True

        dest_dir = tmp_path / "out"
        assert (dest_dir / "warthog.png").exists()
        assert not (dest_dir / "warthog.svg").exists()
