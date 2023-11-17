""" Update service for Joystick Diagrams

Author: Robert Cox
"""
import requests

SERVER_URL = "http://localhost:5000/api/v1/version/"


def get_current_version() -> str:
    """Get current version from file"""
    return "1.0.0"


def check_server_version() -> str:
    """Query API with current version, and handle response"""
    current_version = get_current_version()
    response = requests.get(SERVER_URL + current_version)
    if response.status_code == 200:
        return response.json()
    else:
        return "Error"


def check_templates_hash() -> bool:
    """Check the hash of the templates directory against API hash"""


if __name__ == "__main__":
    pass
