import pathlib
import sys
from setuptools import find_packages
from cx_Freeze import setup, Executable
import joystick_diagrams.version as ver

VER = ver.VERSION
HERE = pathlib.Path(__file__).parent.resolve()
BASE = None
TARGET_NAME: str = "joystick_diagrams"
LONG_DESC = (HERE / "readme.md").read_text(encoding="utf-8")

try:
    from cx_Freeze.hooks import get_qt_plugins_paths
except ImportError:
    include_files = []
else:
    # Inclusion of extra plugins (new in cx_Freeze 6.8b2)
    # cx_Freeze imports automatically the following plugins depending of the
    # use of some modules:
    # imageformats - QtGui
    # platforms - QtGui
    # mediaservice - QtMultimedia
    # printsupport - QtPrintSupport
    #
    # So, "platforms" is used here for demonstration purposes.
    include_files = get_qt_plugins_paths("PyQt5", "QtGui")

if sys.platform == "win32":
    BASE = "Win32GUI"
    TARGET_NAME = "joystick_diagrams.exe"

extra_includes = ["./images", "./templates", "./config.cfg", "./readme.md"]
include_files.extend(extra_includes)

build_options = {
    "include_files": include_files,
    "excludes": ["tkinter", "test", "http", "email", "distutils", "ssl", "asyncio", "concurrent", "pyqt5"],
    "optimize": 2,
}

setup(
    name="Joystick Diagrams",
    version=ver,
    description="Automatically create diagrams for your throttles, joysticks and custom HID devices",
    long_description=LONG_DESC,
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
            base=BASE,
            target_name=TARGET_NAME,
            icon=pathlib.Path("images", "logo.ico"),
            copyright="Robert Cox - joystick-diagrams.com",
        )
    ],
)
