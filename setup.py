# -*- coding: utf-8 -*-
#!/usr/bin/env python

import os
import sys

import django-gcse

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

version = gcse.__version__

if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    print("You probably want to also tag the version now:")
    print("  git tag -a %s -m 'version %s'" % (version, version))
    print("  git push --tags")
    sys.exit()

readme = open('README.rst').read()
history = open('HISTORY.rst').read().replace('.. :changelog:', '')

setup(
    name='django-gcse',
    version=version,
    description='A django reusable application for maintaining websites/data for use with Google Custom Search Engines.',
    long_description=readme + '\n\n' + history,
    author='Steve Schwarz',
    author_email='steve@agilitynerd.com',
    url='https://github.com/saschwarz/django-gcse',
    packages=[
        'gcse',
    ],
    include_package_data=True,
    install_requires=[
    ],
    license="BSD",
    zip_safe=False,
    keywords='django-gcse',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
    ],
)
