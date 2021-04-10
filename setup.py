import pathlib
import sys
import src.version as ver
from setuptools import find_packages
from cx_Freeze import setup, Executable

## Import SRC
sys.path.insert(0, "./src")

ver = ver.VERSION
here = pathlib.Path(__file__).parent.resolve()
base = None
long_description = (here / "readme.md").read_text(encoding="utf-8")

if sys.platform == "win32":
    base = "Win32GUI"

build_options = {
    "include_files": [
        "./images",
        "./templates",
        "./config.cfg",
        "./readme.md",
    ],
    "excludes": ["tkinter", "test", "http", "email", "distutils", "ssl"],
    "optimize": 2,
}

setup(
    name="Joystick Diagrams",
    version=ver,
    description="Automatically create diagrams for your throttles, joysticks and custom HID devices",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Rexeh/joystick-diagrams",
    author="Robert Cox",
    keywords="joystick, HID, diagrams, joystick gremlin, dcs world",
    packages=find_packages(),
    python_requires=">=3.8, <4",
    install_requires=[
        "cx-freeze",
        "pyqt5",
        "ply",
        "pytest",
        "pytest-qt",
        "pytest-cov",
        "black",
        "pre-commit",
    ],
    project_urls={
        "Documentation": "https://joystick-diagrams.com/",
        "Bug Reports": "https://github.com/Rexeh/joystick-diagrams/issues",
        "Funding": "https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=WLLDYGQM5Z39W&source=url",
        "Source": "https://github.com/Rexeh/joystick-diagrams/src",
    },
    options={"build_exe": build_options},
    executables=[
        Executable(
            "./src/joystick_diagrams.py",
            base=base,
            icon="./images/logo.ico",
            copyright="Robert Cox - joystick-diagrams.com",
        )
    ],
)
