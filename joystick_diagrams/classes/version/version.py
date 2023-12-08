""" 
Versioning for Joystick Diagrams

Author: https://github.com/Rexeh
"""
import json
import logging
import os
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import requests

_LOGGER = logging.getLogger(__name__)

VERSION = "2.0 ALPHA"  # Format Major.Minor
VERSION_SERVER = "https://www.joystick-diagrams.com/"
TEMPLATE_DIR = "./templates"
MANIFEST_DIR = "./"
MANIFEST_FILE = "version_manifest.json"
ENCODING = "UTF8"


@dataclass(eq=False)
class JoystickDiagramVersion:
    version: str
    template_hashes: dict

    # Temporary EQ override as templates are not yet integrated to avoid incorrect version checks
    def __eq__(self, other):
        me = float(self.version.split()[0])
        other = float(other.version.split()[0])
        return me >= other


class VersionEncode(json.JSONEncoder):
    def default(self, o: JoystickDiagramVersion) -> Any:
        return {"version": o.version, "template_hashes": o.template_hashes}


def fetch_remote_manifest() -> str | None:
    try:
        return requests.get(VERSION_SERVER + MANIFEST_FILE, timeout=3).text
    except requests.Timeout as timeout:
        _LOGGER.error(f"Unable to reach server for version check: {timeout}")
    return None


def fetch_local_manifest() -> str | None:
    try:
        return open(os.path.join(MANIFEST_DIR, MANIFEST_FILE), "r", encoding=ENCODING).read()
    except OSError as error:
        _LOGGER.error(f"Unable to find local manifest. {error}")
    return None


def performn_version_check() -> bool:
    """Checks the local version against the latest release#

    Returns True for Matched Versions
    Returns False for Unmatched Versions
    """

    remote_manifest = fetch_remote_manifest()
    local_manifest = fetch_local_manifest()

    if not remote_manifest or not local_manifest:
        _LOGGER.error("Unable to perform version check due to an error")
        return True

    running_version = __convert_json_to_object(local_manifest)
    latest_version = __convert_json_to_object(remote_manifest)

    return compare_versions(latest_version=latest_version, running_version=running_version)


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

    with open(os.path.join(MANIFEST_DIR, MANIFEST_FILE), "w", encoding=ENCODING) as output_file:
        output_file.write(dump)

    return ver


def generate_template_manifest() -> dict[str, str]:
    templates = Path(TEMPLATE_DIR)
    manifest: dict[str, str] = {}

    # Generate Template Manifest
    for template in templates.iterdir():
        if template.is_dir():
            continue
        if template.suffix != ".svg":
            continue
        with open(template, "rb", buffering=0) as file:
            manifest[template.name] = sha256(file.read()).hexdigest()

    return manifest


def compare_versions(running_version: JoystickDiagramVersion, latest_version: JoystickDiagramVersion) -> bool:
    """Compares versions based on object __eq__

    Returns TRUE for MATCH
    """
    return running_version == latest_version


def get_current_version() -> str:
    return VERSION


if __name__ == "__main__":
    generate_version()
