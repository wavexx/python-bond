#!/usr/bin/env python
from setuptools import setup, find_packages
setup(name='bond',
      version='0.1',
      packages=find_packages('src'),
      package_dir={'':'src'},
      setup_requires=['nose'],
      test_suite='nose.collector',
      install_requires=['pexpect'])
