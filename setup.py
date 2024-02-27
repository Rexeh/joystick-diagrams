import sys

from cx_Freeze import Executable, setup

BASE = "Win32GUI" if sys.platform == "win32" else None
TARGET_NAME = "joystick_diagrams.exe"

setup(
    url="https://github.com/Rexeh/joystick-diagrams",
    author="Robert Cox",
    keywords="joystick, HID, diagrams, joystick gremlin, dcs world",
    # python_requires=">=3.11, <4",
    install_requires=["cx-freeze", "pyside6", "ply"],
    project_urls={
        "Documentation": "https://joystick-diagrams.com/",
        "Bug Reports": "https://github.com/Rexeh/joystick-diagrams/issues",
        "Funding": "https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=WLLDYGQM5Z39W&source=url",
        "Source": "https://github.com/Rexeh/joystick-diagrams",
    },
    executables=[
        Executable(
            "joystick_diagrams/__main__.py",
            base=BASE,
            target_name=TARGET_NAME,
            copyright="Robert Cox - joystick-diagrams.com",
            icon="./img/logo.ico",
        )
    ],
)
