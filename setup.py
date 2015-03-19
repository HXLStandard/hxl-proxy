#!/usr/bin/python

from setuptools import setup
dependency_links=[
    'git+https://github.com/Toblerity/Shapely.git@maint#egg=Shapely',
]

setup(
    name = 'hxl-proxy',
    packages = ['hxl_proxy'],
    version = '0.0.1',
    description = 'Flask-based web proxy for HXL',
    author='David Megginson',
    author_email='contact@megginson.com',
    url='https://github.com/HXLStandard/hxl-proxy',
    install_requires=['flask', 'libhxl', 'ckanapi'],
    test_suite = "tests",
    tests_require = {
        'test': ['mock']
    }
)
