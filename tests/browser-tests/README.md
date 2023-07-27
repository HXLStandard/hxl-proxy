Links for in-browser tests
==========================

This directory contains lists of URLs for quick (at-a-glance) in-browser tests for the HXL Proxy.

# Usage

    $ cat FILE | xargs -d '\n' firefox
 
 for macos users
 
    $ for url in $(cat tests/browser-tests/URL_FILE); do open $url; done

# Available URL files

* local-urls.txt - development test links for a local server running inside Python at localhost:5000 (make run-dev)
* dev-urls.txt - pre-release dev test links for dev.proxy-hxlstandard-org.ahconu.org
* staging-urls.txt - pre-release staging test links for stage.proxy-hxlstandard-org.ahconu.org
* prod-urls.txt - production test links for proxy.hxlstandard.org
