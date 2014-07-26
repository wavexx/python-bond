#!/usr/bin/env python
from setuptools import setup, find_packages
setup(name='python-bond',
      description='Ambivalent bonds between Python and other languages',
      version='0.1',
      url="https://github.com/wavexx/python-bond",
      author="Yuri D'Elia",
      author_email="wavexx@thregr.org",
      license="GPL2",

      packages=find_packages(),
      include_package_data=True,
      exclude_package_data = {'': ['.gitignore']},

      install_requires=['pexpect'],

      setup_requires=['nose', 'setuptools_git'],
      test_suite='nose.collector')
