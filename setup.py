"""
The setup file_name.
If development mode (=changes in package code directly delivered to python) `pip install -e .` in directory of this file_name
"""

from setuptools import setup, find_packages
from aws_iot import __version__

# https://python-packaging.readthedocs.io/en/latest/minimal.html

with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name="aws_iot",
    version=__version__,
    description="easing interaction with AWS IoT",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Jan Lukas Braje",
    author_email="aws_iot@getkahawa.com",
    packages=find_packages(),
    python_requires=">=3.8",
    zip_safe=False,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.8",
    ],
    # https://pypi.org/pypi?%3Aaction=list_classifiers
    install_requires=["boto3", "AWSIoTPythonSDK"],
    extra_require={"testing": ["pytest", "moto", "freezegun"]},
)
