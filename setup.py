from setuptools import setup, find_packages
import pathlib
from cx_Freeze import setup, Executable
import sys

## Import SRC
sys.path.insert(0,'./src')

here = pathlib.Path(__file__).parent.resolve()
base = None
long_description = (here / 'README.md').read_text(encoding='utf-8')

if sys.platform == "win32":
    base = "Win32GUI"

files = {"include_files": [
                        "./images",
                        "./templates",
                        "./config.cfg",
                       ],
                       }

setup(
    name='Joystick Diagrams',
    version='1.0.0',
    description='Automatically create diagrams for your throttles, joysticks and custom HID devices',
    long_description=long_description, 
    long_description_content_type='text/markdown',
    url='https://github.com/Rexeh/joystick-diagrams', 
    author='Robert Cox',
    keywords='joystick, HID, diagrams, joystick gremlin',

    #scripts = ['./src/joystick-diagram.py'],
    # You can just specify package directories manually here if your project is
    # simple. Or you can use find_packages().
    #
    # Alternatively, if you just want to distribute a single Python file, use
    # the `py_modules` argument instead as follows, which will expect a file
    # called `my_module.py` to exist:
    #
    #   py_modules=["my_module"],
    #
    packages=find_packages(),  # Required

    # Specify which Python versions you support. In contrast to the
    # 'Programming Language' classifiers above, 'pip install' will check this
    # and refuse to install the project if the version does not match. See
    # https://packaging.python.org/guides/distributing-packages-using-setuptools/#python-requires
    python_requires='>=3.8, <4',

    # This field lists other packages that your project depends on to run.
    # Any package you put here will be installed by pip when your project is
    # installed, so they must be valid existing projects.
    #
    # For an analysis of "install_requires" vs pip's requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=['pillow'],  # Optional

    # List additional groups of dependencies here (e.g. development
    # dependencies). Users will be able to install these using the "extras"
    # syntax, for example:
    #
    #   $ pip install sampleproject[dev]
    #
    # Similar to `install_requires` above, these must be valid existing
    # projects.
    extras_require={  # Optional
        'dev': ['check-manifest'],
        'test': ['coverage'],
    },

    # If there are data files included in your packages that need to be
    # installed, specify them here.
    package_data={  # Optional
        'sample': ['package_data.dat'],
    },

    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/distutils/setupscript.html#installing-additional-files
    #
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    data_files=[('my_data', ['data/data_file'])],  # Optional

    project_urls={  # Optional
        'Bug Reports': 'https://github.com/Rexeh/joystick-diagrams/issues',
        'Funding': 'https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=WLLDYGQM5Z39W&source=url',
        'Source': 'https://github.com/Rexeh/joystick-diagrams/src',
    },

    options={'build_exe': files},
    executables = [Executable("./src/joystick-diagram.py", base = base, icon = './images/logo.ico')]
)