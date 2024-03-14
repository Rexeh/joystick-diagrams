import sys

from cx_Freeze import Executable, setup

BASE = "Win32GUI" if sys.platform == "win32" else None
TARGET_NAME = "joystick_diagrams"

executables = [
    Executable(
        "joystick_diagrams/__main__.py",
        base=BASE,
        target_name=TARGET_NAME,
        copyright="Robert Cox - joystick-diagrams.com",
        icon="./img/logo.ico",
        uac_admin=True,
    )
]

setup(
    executables=executables,
)
