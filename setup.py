#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='velbus',
    version='0.0.1',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    python_requires=">=3.6",
    install_requires=[
        'pyserial-asyncio',
        'websockets<4.0',  # https://github.com/channelcat/sanic/issues/1009
        'sanic',
        'bitstruct',
        'attrs>=17.3.0',
    ],
    setup_requires=[
        'pytest-runner'
    ],
    tests_require=[
        'pytest',
        'pytest-asyncio',
    ],
)
