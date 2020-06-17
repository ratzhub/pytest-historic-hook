#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

setup_requirements = ['pytest-runner', ]

setup(
    author="Shiva Adirala",
    author_email='adiralashiva8@gmail.com',
    description='Custom listener to store execution results into MYSQL DB, which is used for pytest-historic report',
    classifiers=[
        'Framework :: Pytest',
        'Programming Language :: Python',
        'Topic :: Software Development :: Testing',
        'Programming Language :: Python :: 3.7',
    ],
    license="MIT license",
    include_package_data=True,
    keywords=[
        'pytest', 'py.test', 'historic',
    ],
    name='pytest-historic-hook',
    packages=find_packages(include=['pytest_historic_hook']),
    setup_requires=setup_requirements,
    url='https://github.com/adiralashiva8/pytest-historic-hook',
    version='0.1.2',
    zip_safe=True,
    install_requires=[
        'pytest',
        'pytest-runner',
        'mysql-connector',
        'httplib2',
    ],
    entry_points={
        'pytest11': [
            'pytest-historic-hook = pytest_historic_hook.plugin',
        ]
    }
)
