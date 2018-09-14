#!/usr/bin/env python

from setuptools import setup

with open('README.rst') as file:
    readme = file.read()

setup(
    name = 'embalm',
    version = '0.2.0',
    author = 'Ken Kundert',
    author_email = 'embalm@nurdletech.com',
    description = 'Duplicity front end.',
    long_description = readme,
    download_url = 'https://github.com/kenkundert/embalm/tarball/master',
    license = 'GPLv3+',
    packages = 'embalm'.split(),
    package_data = {'embalm': ['words']},
    entry_points = {'console_scripts': ['embalm=embalm.main:main']},
    install_requires = 'appdirs arrow docopt inform>=1.9 shlib>=0.8'.split(),
    setup_requires = 'pytest-runner>=2.0'.split(),
    tests_require = 'pytest'.split(),
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Security :: Cryptography',
        'Topic :: Utilities',
    ],
)
