""" 
Versioning for Joystick Diagrams

Author: Robert Cox
"""
import requests
from dataclasses import dataclass

VERSION = "1.4.1"
VERSION_SERVER = "http://localhost:5000/api/v1/version/"


@dataclass
class version:
    version: str
    template_hashes: dict


@staticmethod
def get_current_version() -> str:
    return VERSION


def check_server_version() -> str:
    """Query API with current version, and handle response"""
    pass


def check_templates_hash() -> bool:
    """Check the hash of the templates directory against API hash"""
    pass


def validate_json() -> version:
    pass


def generate_version() -> None:
    pass


def compare_versions(a: version, b: version) -> None:
    pass


if __name__ == "__main__":
    pass
