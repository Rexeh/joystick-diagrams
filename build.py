import pathlib
import sys
import joystick_diagrams.version as ver
from setuptools import find_packages
from cx_Freeze import setup, Executable


ver = ver.VERSION
here = pathlib.Path(__file__).parent.resolve()
base = None
targetName = "joystick_diagrams"
long_description = (here / "readme.md").read_text(encoding="utf-8")

if sys.platform == "win32":
    base = "Win32GUI"
    targetName = "joystick_diagrams.exe"

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
        "coveralls",
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
            "src/joystick_diagrams/main.py",
            base=base,
            target_name=targetName,
            icon=pathlib.Path("images", "logo.ico"),
            copyright="Robert Cox - joystick-diagrams.com",
        )
    ],
)
