import setuptools

import os
from os import listdir
from os.path import isfile, join
mypath = os.path.dirname(os.path.abspath(__file__))
print([f for f in listdir(mypath) if isfile(join(mypath, f))])


REQUIREMENTS = [
    'ujson',
    'sanic',
    'cryptography'
]

TEST_REQUIREMENTS = []

with open("README.md", "r") as fh:
    LONG_DESCRIPTION = fh.read()

setuptools.setup(

    name='sanic_cookies',
    version="0.3.8",
    author='Omar Ryhan',
    author_email='omarryhan@gmail.com',
    license='GNU',
    description="Sanic Cookie and Session Management",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    install_requires=REQUIREMENTS,
    tests_require=TEST_REQUIREMENTS,
    url='https://github.com/omarryhan/sanic-cookies',
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Operating System :: OS Independent",
    ],
    extras_require={
    },
)