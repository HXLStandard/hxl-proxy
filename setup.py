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
    project_urls={
        'Documentation': 'https://github.com/HXLStandard/hxl-proxy/wiki',
        'GitHub': 'https://github.com/HXLStandard/hxl-proxy/',
        'Changelog': 'https://github.com/HXLStandard/hxl-proxy/blob/prod/CHANGELOG',
    },
    author='David Megginson',
    author_email='contact@megginson.com',
    url='https://github.com/HXLStandard/hxl-proxy',
    include_package_data = True,
    zip_safe = False,
    install_requires=[
        'urllib3==1.25.5',       # avoid caching bug
        'requests_cache==0.9.8', # avoid caching bug
        'ckanapi>=3.5',
        'flask>=2.1.2',
        'mysql-connector-python>=8.0.29',
        'libhxl @ git+https://github.com/HXLStandard/libhxl-python.git@dev', # for development
        #'libhxl==5.01', # for release
        'flask-caching',
        'redis',
        'requests',
        'structlog',
    ],
    dependency_links=[
        "git+https://github.com/HXLStandard/libhxl-python@dev#egg=libhxl",
    ],
    test_suite = "tests",
    tests_require = ['mock']
)
