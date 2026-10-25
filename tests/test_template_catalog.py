"""Template catalogue: enumeration, fit (with its cache), control names, Starter copy."""

from pathlib import Path
from unittest.mock import patch

import pytest

from joystick_diagrams import template_catalog as catalog
from joystick_diagrams.export_device import ExportDevice
from joystick_diagrams.input.axis import Axis, AxisDirection, AxisSlider
from joystick_diagrams.input.button import Button
from joystick_diagrams.input.device import Device_
from joystick_diagrams.input.hat import Hat, HatDirection

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLED_COUNT = 46  # .svg files under templates/, .bkp excluded
TEST_TEMPLATE = REPO_ROOT / "tests" / "data" / "template_test.svg"


@pytest.fixture(autouse=True)
def data_root(tmp_path):
    root = tmp_path / "data_root"
    root.mkdir()
    catalog.clear_caches()
    with patch("joystick_diagrams.utils.data_root", return_value=root):
        yield root
    catalog.clear_caches()


def _device() -> Device_:
    dev = Device_("12345678-1234-5678-1234-567812345678", "Test Device")
    dev.create_input(Button(90), "a")
    dev.create_input(Button(2), "b")
    dev.create_input(Axis(AxisDirection.X), "x")
    dev.create_input(Axis(AxisDirection.RZ), "rz")
    dev.create_input(AxisSlider(1), "s")
    dev.create_input(Hat(1, HatDirection.D), "d")
    dev.create_input(Hat(3, HatDirection.U), "u")
    return dev


class TestEnumeration:
    def test_bundled_count_and_no_backups(self):
        infos = catalog.bundled_templates()
        assert len(infos) == BUNDLED_COUNT
        assert all(info.path.suffix == ".svg" for info in infos)
        assert not any(".bkp" in info.path.name for info in infos)
        assert not any(info.path.name.startswith(".") for info in infos)
        assert all(info.source == "bundled" for info in infos)
        assert all(info.key.startswith("bundled:") for info in infos)
        assert all(len(info.content_hash) == 64 for info in infos)

    def test_makers_are_top_level_folders_and_empty_folders_absent(self):
        makers = catalog.makers(catalog.bundled_templates())
        assert "MOZA" not in makers  # empty folder
        assert {"CH", "Thrustmaster", "VKB Sim", "WinWing", "Virpil"} <= set(makers)
        nested = [i for i in catalog.bundled_templates() if i.name == "ICP"]
        assert nested and nested[0].maker == "WinWing"  # WinWing/ICP/ICP.svg

    def test_starter_template_has_no_maker(self):
        starters = [i for i in catalog.bundled_templates() if i.is_starter]
        assert len(starters) == 1
        assert starters[0].maker == ""
        assert starters[0].name == "Starter Template"
        assert catalog.starter_template().key == starters[0].key

    def test_sorted_by_maker_then_name(self):
        infos = catalog.bundled_templates()
        keys = [(i.maker.casefold(), i.name.casefold()) for i in infos]
        assert keys == sorted(keys)

    def test_user_templates_from_my_templates_folder(self, data_root):
        assert catalog.user_templates() == []
        folder = data_root / "templates" / "My templates"
        (folder / "Mine.svg").write_bytes(TEST_TEMPLATE.read_bytes())
        (folder / ".$Mine.svg.bkp").write_bytes(b"x")
        (folder / "notes.txt").write_text("x")
        infos = catalog.user_templates()
        assert [i.name for i in infos] == ["Mine"]
        assert infos[0].source == "user"
        assert infos[0].maker == "My templates"
        assert infos[0].key.startswith("user:")
        assert len(catalog.all_templates()) == BUNDLED_COUNT + 1
        assert catalog.find(infos[0].key) == infos[0]
        assert catalog.find("bundled:nope.svg") is None


class TestControlLabels:
    @pytest.mark.parametrize(
        ("identifier", "label"),
        [
            ("button_31", "Button 31"),
            ("BUTTON_1", "Button 1"),
            ("pov_3_u", "Hat 3 Up"),
            ("pov_1_dl", "Hat 1 Down Left"),
            ("axis_z", "Axis Z"),
            ("axis_rx", "Axis RX"),
            ("axis_slider_1", "Slider 1"),
        ],
    )
    def test_control_label(self, identifier, label):
        assert catalog.control_label(identifier) == label


class TestFit:
    def _info(self, path: Path = TEST_TEMPLATE) -> catalog.TemplateInfo:
        return catalog.info_for_path(path)

    def test_missing_controls_follow_check_compatibility(self):
        device = _device()
        info = self._info()
        result = catalog.fit(info, device)
        export_device = ExportDevice(device, None, None)
        export_device.template = catalog.template_for(info)
        expected = {catalog.control_label(c) for c in export_device.errors}
        assert set(result.missing) == expected
        assert result.total_bound == 7
        assert result.fits_all is False
        assert result.fitted == 7 - len(expected)
        # buttons first by number, then hats, then axes
        assert list(result.missing) == sorted(
            result.missing, key=lambda m: ("BHAS".index(m[0]), m)
        )

    def test_fit_accepts_export_device_and_several_devices(self):
        device = _device()
        info = self._info()
        single = catalog.fit(info, device)
        assert catalog.fit(info, ExportDevice(device, None, None)) == single
        other = Device_(device.guid, device.name)
        other.create_input(Button(2), "same")
        assert catalog.fit(info, [device, other]) == single
        third = Device_(device.guid, device.name)
        third.create_input(Button(77), "new")
        combined = catalog.fit(info, [device, third])
        assert combined.total_bound == 8
        assert "Button 77" in combined.missing

    def test_fits_all_when_every_control_has_a_box(self):
        device = Device_("12345678-1234-5678-1234-567812345678", "D")
        device.create_input(Button(1), "a")
        result = catalog.fit(self._info(), device)
        assert result.fits_all and result.missing == ()
        assert catalog.fit_text(result) == "Has all 1 controls you use"
        assert (
            catalog.fit_text(catalog.fit(self._info(), None)) == "No bindings to check"
        )

    def test_fit_is_cached_by_template_and_bound_set(self):
        info = self._info()
        device = _device()
        with patch(
            "joystick_diagrams.template_catalog.missing_controls",
            wraps=catalog.missing_controls,
        ) as spy:
            first = catalog.fit(info, device)
            again = catalog.fit(info, _device())  # same controls, new object
            assert first is again
            assert spy.call_count == 1
            device.create_input(Button(5), "more")
            changed = catalog.fit(info, device)
            assert changed.total_bound == first.total_bound + 1
            assert spy.call_count == 2
        with patch("joystick_diagrams.template_catalog.Template") as template_cls:
            catalog.fit(info, _device())
            template_cls.assert_not_called()  # the parse is cached too

    def test_fit_on_a_real_template(self):
        vkb = next(
            i for i in catalog.bundled_templates() if "Gladiator NXT R" in i.name
        )
        device = Device_("12345678-1234-5678-1234-567812345678", "VKB")
        device.create_input(Button(1), "a")
        device.create_input(Button(200), "b")
        result = catalog.fit(vkb, device)
        assert result.missing == ("Button 200",)
        assert catalog.fit_text(result) == "1 of 2 controls fit"


class TestStarterCopy:
    def test_copies_into_my_templates_named_after_the_controller(self, data_root):
        created = catalog.create_from_starter("VKBsim Gladiator NXT R")
        assert created.path == data_root / "templates" / "My templates" / (
            "VKBsim Gladiator NXT R.svg"
        )
        assert created.path.read_bytes() == catalog.starter_template().path.read_bytes()
        assert created.template_key.startswith("user:")
        assert created.info.source == "user"
        assert created.info.name == "VKBsim Gladiator NXT R"
        assert created.info.content_hash == catalog.starter_template().content_hash
        assert created.info in catalog.user_templates()

    def test_unique_on_collision(self):
        first = catalog.create_from_starter("Stick")
        second = catalog.create_from_starter("Stick")
        third = catalog.create_from_starter("Stick")
        assert first.path.name == "Stick.svg"
        assert second.path.name == "Stick 2.svg"
        assert third.path.name == "Stick 3.svg"

    @pytest.mark.parametrize(
        ("name", "stem"),
        [
            ('Throttle - HOTAS "Warthog"', "Throttle - HOTAS Warthog"),
            ("A/B:C*D?E<F>G|H\\I", "ABCDEFGHI"),
            ("   lots   of   space  ", "lots of space"),
            ("...", "My controller"),
            ("", "My controller"),
        ],
    )
    def test_sanitised_names(self, name, stem):
        assert catalog.safe_file_stem(name) == stem
        assert catalog.create_from_starter(name).path.stem == stem
