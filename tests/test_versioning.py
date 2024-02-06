from dataclasses import dataclass
from unittest.mock import mock_open, patch

import pytest
import requests

from joystick_diagrams.classes.version import version


# Object creation
def test_version_creation_string_full_semver():
    ver = version.JoystickDiagramVersion("1.5.0", {})
    assert ver.version == "1.5.0"
    assert ver.semantic_version.major == 1
    assert ver.semantic_version.minor == 5
    assert ver.semantic_version.patch == 0


def test_version_creation_string_two_part_semver():
    ver = version.JoystickDiagramVersion("1.3", {})
    assert ver.version == "1.3"
    assert ver.semantic_version.major == 1
    assert ver.semantic_version.minor == 3
    assert ver.semantic_version.patch == 0


def test_version_creation_string_one_part_semver():
    ver = version.JoystickDiagramVersion("1", {})
    assert ver.version == "1"
    assert ver.semantic_version.major == 1
    assert ver.semantic_version.minor == 0
    assert ver.semantic_version.patch == 0


def test_version_creation_string_invalid_semver():
    with pytest.raises(ValueError):
        version.JoystickDiagramVersion("Potato", {})


def test_version_creation_int_failure():
    with pytest.raises(ValueError):
        version.JoystickDiagramVersion(1, {})


## Json deserialise


def test_json_to_object():
    json_string = '{"version": "2.0", "template_hashes": {"hash_item_one" : "123"}}'
    returned_ver = version.__convert_json_to_object(json_string)
    assert isinstance(returned_ver, version.JoystickDiagramVersion)
    assert returned_ver.version == "2.0"
    assert "hash_item_one" in returned_ver.template_hashes


## Remote/Local manifest retrieval and comparisons
@pytest.fixture
def request_exception_mock(monkeypatch):

    def mock(*args, **kwargs):
        raise requests.exceptions.RequestException

    monkeypatch.setattr(requests, "get", mock)


## Remote/Local manifest retrieval and comparisons
@pytest.fixture
def fetch_remote_mock(monkeypatch):
    @dataclass
    class MockRequestObject:
        text: str

    def mock(*args, **kwargs):
        mock_text = '{"version": "2.0", "template_hashes": {"hash_item_one" : "123"}}'
        return MockRequestObject(mock_text)

    monkeypatch.setattr(requests, "get", mock)


def test_remote_manifest(fetch_remote_mock):
    data = version.fetch_remote_manifest()

    assert data == '{"version": "2.0", "template_hashes": {"hash_item_one" : "123"}}'


def test_remote_manifest_request_fail(request_exception_mock, caplog):

    data = version.fetch_remote_manifest()

    assert data is None
    assert "Unable to reach server for version check" in caplog.text


@pytest.fixture
def fetch_local_mock(monkeypatch):
    def mock():
        return '{"version": "2.0", "template_hashes": {"hash_item_one" : "123"}}'

    monkeypatch.setattr(version, "fetch_local_manifest", mock)


def test_local_manifest(fetch_local_mock):
    data = version.fetch_local_manifest()

    assert data == '{"version": "2.0", "template_hashes": {"hash_item_one" : "123"}}'


def test_perform_version_check(fetch_local_mock, fetch_remote_mock):
    check = version.perform_version_check()
    assert check is True


## Version checking


def test_check_equal_versions():
    local_version = version.JoystickDiagramVersion("1.0.0", {})
    remote_version = version.JoystickDiagramVersion("1.0.0", {})

    check = version.compare_versions(local_version, remote_version)

    assert check is True


def test_check_local_higher_than_remote():
    local_version = version.JoystickDiagramVersion("1.0.1", {})
    remote_version = version.JoystickDiagramVersion("1.0.0", {})

    check = version.compare_versions(local_version, remote_version)

    assert check is True


def test_check_local_less_than_remote():
    local_version = version.JoystickDiagramVersion("1.0.0", {})
    remote_version = version.JoystickDiagramVersion("1.0.1", {})

    check = version.compare_versions(local_version, remote_version)

    assert check is False


def test_version_object_json_encode():

    version_string = "1.0.0"
    temp_dict = {"hash_one": "one"}
    ver = version.JoystickDiagramVersion(version_string, temp_dict)

    encode = version.VersionEncode().default(ver)

    assert encode == {"version": version_string, "template_hashes": {"hash_one": "one"}}


def test_generate_version(monkeypatch):

    def mock_generate_template_manifest():
        return {}

    monkeypatch.setattr(version, "generate_template_manifest", mock_generate_template_manifest)

    m = mock_open(read_data="foo bar")
    with patch("joystick_diagrams.classes.version.version.open", m):
        generated = version.generate_version()

    assert isinstance(generated, version.JoystickDiagramVersion)


def test_get_current_version():

    ver_const = version.VERSION

    ver = version.get_current_version()

    assert ver_const == ver
