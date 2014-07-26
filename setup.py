#!/usr/bin/env python
from setuptools import setup
setup(name='bond',
      version='0.1',
      packages=['bond'],
      setup_requires=['nose'],
      test_suite='nose.collector',
      install_requires=['pexpect'])
