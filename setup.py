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
    version = '1.3',
    description = 'Flask-based web proxy for HXL',
    author='David Megginson',
    author_email='contact@megginson.com',
    url='https://github.com/HXLStandard/hxl-proxy',
    include_package_data = True,
    zip_safe = False,
    install_requires=['flask-cache>=0.13', 'libhxl>=4.3', 'ckanapi>=3.5', 'flask>=0.10', 'requests_cache'],
    test_suite = "tests",
    tests_require = ['mock']
)
