import pathlib
import sys
from setuptools import find_packages
from cx_Freeze import setup, Executable


HERE = pathlib.Path(__file__).parent.resolve()
TARGET_NAME: str = "joystick_diagrams"
LONG_DESC = (HERE / "readme.md").read_text(encoding="utf-8")
BASE = "Win32GUI" if sys.platform == "win32" else None
TARGET_NAME = "joystick_diagrams.exe"


def main():
    setup(
        url="https://github.com/Rexeh/joystick-diagrams",
        author="Robert Cox",
        keywords="joystick, HID, diagrams, joystick gremlin, dcs world",
        packages=find_packages(),
        python_requires=">=3.11, <4",
        install_requires=["cx-freeze", "pyqt5", "ply"],
        project_urls={
            "Documentation": "https://joystick-diagrams.com/",
            "Bug Reports": "https://github.com/Rexeh/joystick-diagrams/issues",
            "Funding": "https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=WLLDYGQM5Z39W&source=url",
            "Source": "https://github.com/Rexeh/joystick-diagrams/src",
        },
        executables=[
            Executable(
                "joystick_diagrams/__main__.py",
                base=BASE,
                target_name=TARGET_NAME,
                icon=pathlib.Path("images", "logo.ico"),
                copyright="Robert Cox - joystick-diagrams.com",
            )
        ],
    )


if __name__ == "__main__":
    main()
