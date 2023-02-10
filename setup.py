import pathlib
from distutils.core import setup

from setuptools import find_packages

here = pathlib.Path(__file__).parent.resolve()

# Get the long description from the README file
long_description = (here / "README.md").read_text(encoding="utf-8")

# Derive requirements from requirements.in, so they aren't duplicated
requirements = (here / "requirements.in").read_text(encoding="utf-8").splitlines()

# this will make a package of only the GUI directory
#  as specified by the 'packages' keyword
setup(
    name="gbt_rfi_gui",
    version="1.1",  # 13',
    description="GBT RFI GUI",
    long_description=long_description,
    author="Kathlyn Purcell",
    author_email="kpurcell@nrao.edu",
    url="https://pypi.org/project/gbt-rfi-gui/",
    keywords="",
    packages=find_packages(),
    py_modules=["gbt_rfi_gui"],
    install_requires=requirements,
    python_requires=">=3.6, <4",
    entry_points={
        "console_scripts": [
            "gbt-rfi-gui=gbt_rfi_gui.gbt_rfi_gui:main",
        ],
    },
)
