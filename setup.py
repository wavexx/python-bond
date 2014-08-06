#!/usr/bin/env python
from setuptools import setup, find_packages
setup(name='python-bond', version='0.4',
      description='transparent remote/recursive evaluation between Python and other languages',

      author="Yuri D'Elia",
      author_email="wavexx@thregr.org",
      license="GPL2",
      long_description=open('README.rst').read(),
      url="https://github.com/wavexx/python-bond",
      classifiers=['Development Status :: 5 - Production/Stable',
                   'Environment :: Console',
                   'Environment :: No Input/Output (Daemon)',
                   'Intended Audience :: Developers',
                   'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
                   'Operating System :: POSIX',
                   'Operating System :: Unix',
                   'Programming Language :: JavaScript',
                   'Programming Language :: PHP',
                   'Programming Language :: Perl',
                   'Programming Language :: Python',
                   'Topic :: Software Development :: Interpreters',
                   'Topic :: Software Development'],

      packages=find_packages(),
      include_package_data=True,
      exclude_package_data = {'': ['.gitignore']},

      install_requires=['pexpect', 'setuptools'],
      setup_requires=['nose', 'setuptools_git'],
      test_suite='nose.collector')
