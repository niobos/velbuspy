#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='velbus',
    version='0.0.1',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    python_requires=">=3.7",
    install_requires=[
        'pyserial-asyncio',
        'websockets<9',  # hbmqtt currently (2021-06-07) not compatible with >=9
        'sanic',
        'bitstruct',
        'attrs>=17.3.0',
        'structattr',
        'sortedcontainers',
        'python-dateutil ',
        'hbmqtt',
    ],
    setup_requires=[
        'pytest-runner'
    ],
    tests_require=[
        'pytest',
        'pytest-asyncio',
        'pytest-mock',
        'jsonpatch',
        'freezegun<=1.0.0',  # https://github.com/spulec/freezegun/issues/401
        'sanic[test]',
    ],
)
