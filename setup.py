#!/usr/bin/env python
from setuptools import setup

setup(name='adzerk',
    description='adzerk api wrapper',
    version='0.1',
    author='Brian Simpson',
    author_email='brian@reddit.com',
    packages=['adzerk'],
    install_requires=['requests'],
)
