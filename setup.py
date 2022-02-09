import setuptools
from distutils.core import setup
from setuptools import find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

# Get the long description from the README file
long_description = (here / "README.md").read_text(encoding="utf-8")


# this will make a package of only the GUI directory
#  as specified by the 'packages' keyword
setup(
    name="gbt_rfi_gui",
    version="1.0.13.2",  # 13',
    description="GBT RFI GUI",
    long_description=long_description,
    author="Aaron Lovato, Brenne Gregory",
    author_email="alovato@nrao.edu, bgregory@nrao.edu",
    url="https://pypi.org/project/gbt-rfi-gui/",
    keywords="",
    packages=find_packages(),
    py_modules=["gbt_rfi_gui"],
    install_requires=[
        "Django",
        "django-crispy-forms",
        "django-environ",
        "django-extensions",
        "ipdb",
        "ipython",
        "matplotlib",
        "pandas",
        "PyQt5",
        # 2.9+ drop support for Postgres 9.6+
        "psycopg2<2.9",
        "scipy",
    ],
    python_requires=">=3.6, <4",
    entry_points={
        "console_scripts": [
            "gbt-rfi-gui=gbt_rfi_gui.gbt_rfi_gui:main",
        ],
    },
)
