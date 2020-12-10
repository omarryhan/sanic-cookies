import setuptools

import os
from os import listdir
from os.path import isfile, join

mypath = os.path.dirname(os.path.abspath(__file__))
print([f for f in listdir(mypath) if isfile(join(mypath, f))])


with open("requirements.txt", "r") as f:
    requirements = f.read().splitlines()

with open("test_requirements.txt", "r") as f:
    test_requirements = f.read().splitlines()

with open("README.md", "r", encoding="utf-8") as fh:
    LONG_DESCRIPTION = fh.read()

setuptools.setup(
    name="sanic_cookies",
    version="0.4.3",
    author="Omar Ryhan",
    author_email="omarryhan@gmail.com",
    license="GNU",
    description="Cookies and Session Management for Sanic",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    install_requires=requirements,
    tests_require=test_requirements,
    url="https://github.com/omarryhan/sanic-cookies",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Operating System :: OS Independent",
    ],
    extras_require={},
)
