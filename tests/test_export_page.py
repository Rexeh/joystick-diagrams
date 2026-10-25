"""``export.export_page`` file naming and conversion targets; ``parse_svg_dimensions`` units."""

from dataclasses import dataclass
from pathlib import Path

import pytest

from joystick_diagrams.export import (
    ExportDestination,
    ExportOutput,
    export_page,
    page_profiles,
    safe_file_name,
)
from joystick_diagrams.export_device import ExportDevice
from joystick_diagrams.export_image import parse_svg_dimensions, parse_svg_page_size_mm
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.device import Device_
from joystick_diagrams.render.compose import ComposeError
from joystick_diagrams.render.page import Page, Placement, ProfileRule
from joystick_diagrams.template import Template

REPO_ROOT = Path(__file__).resolve().parents[1]
VKB = REPO_ROOT / "templates" / "VKB Sim" / "VKB-Sim Gladiator NXT R.svg"
STARTER = REPO_ROOT / "templates" / "Starter Template.svg"
GUID_A = "a1b2c3d4-0001-11ee-8001-444553540000"
GUID_B = "a1b2c3d4-0002-11ee-8002-444553540000"


@dataclass
class Wrapper:
    profile_name: str

    @property
    def profile_key(self) -> str:
        return f"dcs_{self.profile_name.lower()}"


def _device(guid: str, name: str, bound: bool = True) -> Device_:
    device = Device_(guid, name)
    if bound:
        device.create_input(Button(1), "Fire")
    return device


def _export_device(device: Device_, path: Path | None, wrapper) -> ExportDevice:
    ed = ExportDevice(device, None, wrapper)
    ed._template = Template(str(path)) if path else None
    return ed


@pytest.fixture
def world():
    f16 = Wrapper("F-16C_50")
    a10 = Wrapper("A-10C_2")
    devices = [
        _export_device(_device(GUID_A, "VKB"), VKB, f16),
        _export_device(_device(GUID_B, "Throttle"), STARTER, f16),
        _export_device(_device(GUID_A, "VKB"), VKB, a10),
    ]
    page = Page(
        name="Stick / Throttle: A4",
        placements=[Placement(device_guid=GUID_A), Placement(device_guid=GUID_B)],
    )
    return page, devices, f16, a10


class TestExportPage:
    def test_svg_only(self, tmp_path, world):
        page, devices, f16, _ = world
        output = export_page(page, f16, devices, None, ExportDestination(tmp_path))
        assert isinstance(output, ExportOutput)
        assert Path(output.svg_path) == tmp_path / "Stick Throttle A4 - F-16C_50.svg"
        assert Path(output.svg_path).is_file()
        assert output.png_path is None and output.pdf_path is None
        assert output.conversion_target is None
        assert output.paths == (output.svg_path, None)
        assert output.report is None
        assert output.compose is not None and output.compose.empty_members == ()
        assert parse_svg_dimensions(Path(output.svg_path)) == (
            1123,
            794,
        )  # A4 landscape
        assert parse_svg_page_size_mm(Path(output.svg_path)) == pytest.approx(
            (297, 210)
        )

    def test_png_and_pdf_targets(self, tmp_path, world):
        page, devices, f16, _ = world
        png = export_page(page, f16, devices, None, ExportDestination(tmp_path, "PNG"))
        assert Path(png.png_path) == tmp_path / "Stick Throttle A4 - F-16C_50.png"
        assert png.conversion_target == png.png_path
        assert not Path(png.png_path).exists()  # converted later by PngConverter
        pdf = export_page(page, f16, devices, None, ExportDestination(tmp_path, "pdf"))
        assert Path(pdf.pdf_path) == tmp_path / "Stick Throttle A4 - F-16C_50.pdf"
        assert pdf.png_path is None
        assert pdf.conversion_target == pdf.pdf_path

    def test_profile_without_a_member_still_exports_dimmed(self, tmp_path, world):
        page, devices, f16, a10 = world
        # Default rule: only the profile where both controllers have bindings
        assert [w.profile_name for w in page_profiles(page, devices)] == ["F-16C_50"]
        page = page.model_copy(update={"profile_rule": ProfileRule.ANY})
        assert [w.profile_name for w in page_profiles(page, devices)] == [
            "F-16C_50",
            "A-10C_2",
        ]
        output = export_page(page, a10, devices, None, ExportDestination(tmp_path))
        assert Path(output.svg_path).name == "Stick Throttle A4 - A-10C_2.svg"
        assert output.compose.empty_members == (GUID_B,)
        assert "No bindings in A-10C_2" in Path(output.svg_path).read_text("utf-8")

    def test_member_without_template_raises(self, tmp_path, world):
        page, devices, f16, _ = world
        devices[1]._template = None
        with pytest.raises(ComposeError, match="Throttle needs a template"):
            export_page(page, f16, devices, None, ExportDestination(tmp_path))

    def test_safe_file_name(self):
        assert safe_file_name('A: "B" <C>?') == "A B C"
        assert safe_file_name("   ") == "Page"
        assert safe_file_name("...", "Profile") == "Profile"

    def test_existing_export_output_shape_unchanged(self):
        output = ExportOutput("a.svg", "a.png", None)
        assert output.paths == ("a.svg", "a.png")
        assert output.pdf_path is None and output.compose is None


class TestParseSvgDimensions:
    @pytest.mark.parametrize(
        ("width", "height", "expected"),
        [
            ('width="1159px" height="807px"', None, (1159, 807)),
            ('width="1159" height="807"', None, (1159, 807)),
            (
                'width="1159.7px" height="807.2px"',
                None,
                (1159, 807),
            ),  # as before: truncated
            ('width="297mm" height="210mm"', None, (1123, 794)),
            ('width="29.7cm" height="21cm"', None, (1123, 794)),
            ('width="8.5in" height="11in"', None, (816, 1056)),
            ('width="72pt" height="36pt"', None, (96, 48)),
            ('width="10pc" height="5pc"', None, (160, 80)),
            ('viewBox="0 0 10 10"', None, (800, 600)),  # defaults
        ],
    )
    def test_units(self, tmp_path, width, height, expected):
        svg = tmp_path / "t.svg"
        svg.write_text(
            f'<?xml version="1.0"?>\n<svg xmlns="http://www.w3.org/2000/svg" {width}><g/></svg>'
        )
        assert parse_svg_dimensions(svg) == expected

    def test_page_size_mm_only_for_physical_units(self, tmp_path):
        svg = tmp_path / "t.svg"
        svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="1159px" height="807px"/>'
        )
        assert parse_svg_page_size_mm(svg) is None
        svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="5.5in" height="8.5in"/>'
        )
        assert parse_svg_page_size_mm(svg) == pytest.approx((139.7, 215.9))
