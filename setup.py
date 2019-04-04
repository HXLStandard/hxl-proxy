#!/usr/bin/python
"""Install, build, or test the HXL Proxy.
For details, try
  python setup.py -h
"""

import sys, setuptools

if sys.version_info.major != 3:
    raise SystemExit("The HXL Proxy requires Python 3.x")

setuptools.setup(
    name = 'hxl-proxy',
    packages = ['hxl_proxy'],
    package_data={'hxl_proxy': ['*.sql']},
    version = "1.15.1",
    description = 'Flask-based web proxy for HXL',
    author='David Megginson',
    author_email='contact@megginson.com',
    url='https://github.com/HXLStandard/hxl-proxy',
    include_package_data = True,
    zip_safe = False,
    install_requires=[
        'requests>=2.11',
        'libhxl==4.15.1',
        'ckanapi>=3.5',
        'flask>=1.0',
        'flask-caching',
        'requests_cache',
        'mysql-connector-python',
        'iati2hxl>=0.2'
    ],
    test_suite = "tests",
    tests_require = ['mock']
)
