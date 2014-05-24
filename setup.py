#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright:
#   2012-2013 Janis Jansons (janis.jansons@janhouse.lv)
#   2014      David Fischer (david.fischer.ch@gmail.com)

from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from codecs import open
from pip.req import parse_requirements
from setuptools import setup, find_packages

# https://pypi.python.org/pypi?%3Aaction=list_classifiers

classifiers = """
Development Status :: 3 - Alpha
Environment :: Console
Intended Audience :: Developers
Intended Audience :: End Users/Desktop
License :: OSI Approved :: MIT License
Natural Language :: English
Operating System :: POSIX :: Linux
Programming Language :: Python
Programming Language :: Python :: 2
Programming Language :: Python :: 2.6
Programming Language :: Python :: 2.7
Programming Language :: Python :: Implementation :: CPython
Topic :: Internet :: WWW/HTTP
Topic :: Utilities
"""

not_yet_tested = """
Programming Language :: Python :: 3
Programming Language :: Python :: 3.3
Programming Language :: Python :: 3.4
Operating System :: MacOS :: MacOS X
Operating System :: Unix
"""

setup(name='tespeed',
      version='0.1.0-alpha',
      packages=find_packages(include=['tespeed']),
      description='TeSpeed, CLI SpeedTest.net',
      long_description=open('README.rst', 'r', encoding='utf-8').read(),
      author='Janis Jansons & David Fischer',
      author_email='janis.jansons@janhouse.lv',
      url='https://github.com/davidfischer-ch/tespeed',
      license='MIT',
      classifiers=filter(None, classifiers.split('\n')),
      keywords=['benchmark', 'download', 'upload', 'network', 'speed', 'internet', 'speedtest.net'],
      dependency_links=[str(requirement.url) for requirement in parse_requirements('requirements.txt')],
      install_requires=[str(requirement.req) for requirement in parse_requirements('requirements.txt')],
      entry_points={
          'console_scripts': [
              'tespeed=tespeed.bin:tespeed'
          ]
      },
      use_2to3=sys.version_info[0] > 2)
