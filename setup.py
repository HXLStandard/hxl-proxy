#!/usr/bin/python

from setuptools import setup
dependency_links=[
    'git+https://github.com/Toblerity/Shapely.git@maint#egg=Shapely',
]

setup(
    name = 'hxl-proxy',
    packages = ['hxl_proxy'],
    version = '0.3',
    description = 'Flask-based web proxy for HXL',
    author='David Megginson',
    author_email='contact@megginson.com',
    url='https://github.com/HXLStandard/hxl-proxy',
    include_package_data = True,
    zip_safe = False,
    install_requires=['flask-cache', 'libhxl>=1.1', 'ckanapi', 'flask', 'psycopg2'],
    test_suite = "tests",
    tests_require = ['mock']
)
