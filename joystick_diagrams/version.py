"""Versioning for Joystick Diagrams.

Used to generate and compare version manifests in order to facilitate update checking.

Author: https://github.com/Rexeh
"""

import json
import logging
import os
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

import requests  # type: ignore
import semver

_LOGGER = logging.getLogger(__name__)

VERSION = "2.0.3"  # Format Major.Minor
VERSION_SERVER = "https://www.joystick-diagrams.com/"
TEMPLATE_DIR = "./templates"
MANIFEST_DIR = "./"
MANIFEST_FILE = "version_manifest.json"
ENCODING = "UTF8"


@dataclass()
class JoystickDiagramVersion:
    version: str
    template_hashes: dict[str, str]
    semantic_version: semver.Version = field(init=False)

    def __post_init__(self):
        if not isinstance(self.version, str):
            raise ValueError("Version must be a string")

        try:
            self.semantic_version = semver.Version.parse(
                self.version, optional_minor_and_patch=True
            )
        except ValueError as e:
            raise ValueError(f"Error creating version from provided string: {e}") from e


class VersionEncode(json.JSONEncoder):
    def default(self, o: JoystickDiagramVersion) -> dict:
        return {"version": o.version, "template_hashes": o.template_hashes}


def fetch_remote_manifest() -> str | None:
    try:
        return requests.get(VERSION_SERVER + MANIFEST_FILE, timeout=3).text
    except requests.exceptions.RequestException as request_exp:
        _LOGGER.error(f"Unable to reach server for version check: {request_exp}")
    return None


def fetch_local_manifest() -> str | None:
    try:
        with open(
            os.path.join(MANIFEST_DIR, MANIFEST_FILE), "r", encoding=ENCODING
        ) as file:
            return file.read()
    except OSError as error:
        _LOGGER.error(f"Unable to find local manifest. {error}")
    return None


def perform_version_check() -> bool:
    """Checks the local version against the latest release.

    Returns True for Matched Versions
    Returns False for Unmatched Versions
    """
    remote_manifest = fetch_remote_manifest()
    local_manifest = fetch_local_manifest()

    if not remote_manifest or not local_manifest:
        _LOGGER.error(
            "Unable to perform version check due to one or more manifests not being present."
        )
        return True

    running_version = __convert_json_to_object(local_manifest)
    latest_version = __convert_json_to_object(remote_manifest)

    return compare_versions(
        latest_version=latest_version, running_version=running_version
    )


def __convert_json_to_object(payload: str) -> JoystickDiagramVersion:
    json_dictionary = json.loads(payload)

    try:
        return JoystickDiagramVersion(**json_dictionary)
    except TypeError as e:
        _LOGGER.error(e)
        raise


def generate_version(version_number: str = VERSION) -> JoystickDiagramVersion:
    """Generate a manifest for package and remote"""
    manifest = generate_template_manifest()
    ver = JoystickDiagramVersion(version=version_number, template_hashes=manifest)

    dump = json.dumps(ver, cls=VersionEncode)

    with open(
        os.path.join(MANIFEST_DIR, MANIFEST_FILE), "w", encoding=ENCODING
    ) as output_file:
        output_file.write(dump)

    return ver


def generate_template_manifest() -> dict[str, str]:
    """Generates a list of hashes for each templatein the package"""
    templates = Path(TEMPLATE_DIR)
    manifest: dict[str, str] = {}

    # Generate Template Manifest
    for template in templates.iterdir():
        # For now no traversal supported
        if template.is_dir():
            continue
        if template.suffix != ".svg":
            continue
        with open(template, "rb", buffering=0) as file:
            manifest[template.name] = sha256(file.read()).hexdigest()

    return manifest


def compare_versions(
    running_version: JoystickDiagramVersion, latest_version: JoystickDiagramVersion
) -> bool:
    """Compares versions based on the running version being less than the latest remote

    Returns TRUE for MATCH
    """
    return running_version.semantic_version >= latest_version.semantic_version


def get_current_version() -> str:
    return VERSION


if __name__ == "__main__":
    pass
