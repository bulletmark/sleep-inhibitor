#!/usr/bin/python3
# Setup script to install this package.
# M.Blakeney, Mar 2018.

from setuptools import setup
from pathlib import Path

name = 'sleep-inhibitor'
module = name.replace('-', '_')
here = Path(__file__).resolve().parent

setup(
    name=name,
    version='1.17',
    description='Program to run plugins to inhibit system '
    'sleep/suspend/hibernate',
    long_description=here.joinpath('README.md').read_text(),
    long_description_content_type="text/markdown",
    url=f'https://github.com/bulletmark/{name}',
    author='Mark Blakeney',
    author_email='mark.blakeney@bullet-systems.net',
    keywords='bash',
    license='GPLv3',
    py_modules=[module],
    python_requires='>=3.7',
    install_requires=['ruamel.yaml'],
    classifiers=[
        'Programming Language :: Python :: 3',
    ],
    data_files=[
        (f'share/{name}', ['README.md', f'{name}.conf', f'{name}.service']),
        (f'share/{name}/plugins/', [str(p) for p in Path('plugins').iterdir()]),
    ],
    entry_points={
        'console_scripts': [f'{name}={module}:main'],
    },
)
