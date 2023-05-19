#!/usr/bin/python
"""Install, build, or test the HXL Proxy.
For details, try
  python setup.py -h
"""

import sys, setuptools

if sys.version_info.major != 3:
    raise SystemExit("The HXL Proxy requires Python 3.x")

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name = 'hxl-proxy',
    packages = ['hxl_proxy'],
    package_data={'hxl_proxy': ['*.sql']},
    version = "2.0",
    description = 'Flask-based web proxy for HXL',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='David Megginson',
    author_email='contact@megginson.com',
    url='https://github.com/HXLStandard/hxl-proxy',
    include_package_data = True,
    zip_safe = False,
    install_requires=[
        'urllib3>=1.21.1,<1.27', # version required by requests
        #'libhxl @ git+https://github.com/HXLStandard/libhxl-python.git@dev', # for development
        'libhxl==5.0', # for release
        'ckanapi>=3.5',
        'flask-caching',
        'flask>=2.1.2',
        'mysql-connector-python>=8.0.29',
        'redis',
        'requests>=2.27',
        'requests_cache',
        'structlog',
    ],
    dependency_links=[
        "git+https://github.com/HXLStandard/libhxl-python@dev#egg=libhxl",
    ],
    test_suite = "tests",
    tests_require = ['mock']
)
