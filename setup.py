#!/usr/bin/env python
from setuptools import setup, find_packages

# long description with latest release notes
readme = open('README.rst').read()
news = open('NEWS.rst').read()
long_description = (readme + "\n\nLatest release notes\n====================\n"
                    + '\n'.join(news.split('\n\n\n', 1)[0].splitlines()[2:]))

# the actual setup
setup(name='python-bond', version='1.0',
      description='transparent remote/recursive evaluation between Python and other languages',

      author="Yuri D'Elia",
      author_email="wavexx@thregr.org",
      license="GPL2",
      long_description=long_description,
      url="https://github.com/wavexx/python-bond",
      keywords="javascript php perl python",
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
                   'Programming Language :: Python :: 2.7',
                   'Programming Language :: Python :: 3',
                   'Programming Language :: Python',
                   'Topic :: Software Development :: Interpreters',
                   'Topic :: Software Development :: Libraries :: Python Modules',
                   'Topic :: Software Development'],

      packages=find_packages(exclude=['tests']),
      include_package_data=True,
      exclude_package_data = {'': ['*.txt', '*.rst']},

      install_requires=['pexpect', 'setuptools'],
      setup_requires=['nose', 'setuptools_git'],
      test_suite='nose.collector')
