########################################################################
# Makefile to automate common tasks
#
# Test-related targets:
#
# (These require the Python3 venv module)
#
# build-venv - (re)build the Python virtual environment if needed
# test - run the unit tests (building a virtual environment if needed)
# test-install - test a fresh installation in a temporary virtual environment
#
# Git-related targets:
#
# (All of these check out the dev branch at the end)
#
# close-issue - merge the current issue branch into dev and delete
# push-dev - push current dev branch to upstream
# merge-test - merge the dev branch into the test branch and push
# merge-master - merge the test branch into the master branch and push
#
# Other:
#
# etags - build an Emacs TAGS file
# restart - touch hxl-proxy.wsgi to restart the app
########################################################################


# figure out what branch we're on currently
BRANCH=$(shell git symbolic-ref --short HEAD)

# activation script for the Python virtual environment
VENV=venv/bin/activate


# run unit tests
test: $(VENV)
	. $(VENV) && python setup.py test

# alias to (re)build the Python virtual environment
build-venv: $(VENV)

remove-venv:
	rm -rf $(VENV)

# (re)build the virtual environment if it's missing, or whenever setup.py changes
$(VENV): setup.py
	rm -rf venv && virtualenv venv
	. $(VENV) && cd ../libhxl-python && python setup.py develop && cd ../hxl-proxy && python setup.py develop

# close the current issue branch and merge into dev
close-issue:
	git checkout dev && git merge "$(BRANCH)" && git branch -d "$(BRANCH)"

# push the dev branch to origin
push-dev:
	git checkout dev && git push

# merge the dev branch into test and push both to origin
merge-test: push-dev
	git checkout test && git merge dev && git push && git checkout dev

# merge the test branch into master and push both to origin
merge-master: merge-test
	git checkout master && git merge test && git push && git checkout dev

# do a cold install in a temporary virtual environment and run unit tests
test-install:
	rm -rf venv-test && python3 -m venv venv-test && . venv-test/bin/activate && python setup.py install && python setup.py test
	rm -rf venv-test # make sure we clean up

# Add target for docker build
test-docker:
	pkexec docker build --no-cache -t "unocha/hxl-proxy:local" `pwd`

# browser tests for dev.proxy.hxlstandard.org
browser-tests-local:
	cat tests/browser-tests/local-urls.txt | xargs -d '\n' firefox

# browser tests for dev.proxy.hxlstandard.org
browser-tests-local-server:
	cat tests/browser-tests/local-server-urls.txt | xargs -d '\n' firefox

# browser tests for beta.proxy.hxlstandard.org
browser-tests-beta:
	cat tests/browser-tests/beta-urls.txt | xargs -d '\n' firefox

# browser tests for dev.proxy-hxlstandard-org.ahconu.org
browser-tests-dev:
	cat tests/browser-tests/dev-urls.txt | xargs -d '\n' firefox

# browser tests for stage.proxy-hxlstandard-org.ahconu.org
browser-tests-staging:
	cat tests/browser-tests/staging-urls.txt | xargs -d '\n' firefox

# browser tests for proxy.hxlstandard.org
browser-tests-prod:
	cat tests/browser-tests/prod-urls.txt | xargs -d '\n' firefox

# run local dev (needs config in local/config.py)
run-dev: $(VENV)
	. $(VENV) && HXL_PROXY_CONFIG=../local/config.py python run-server.py

# publish a new release on PyPi
publish:
	. $(VENV) && pip install twine && rm -rf dist/* && python setup.py sdist && twine upload dist/*

# (re)generate emacs TAGS file
etags:
	find hxl_proxy tests -name '*.py' -o -name '*.csv' -o -name '*.html' -o -name '*.js'| grep -v static/jquery | grep -v static/bootstrap | grep -v static/compat | xargs etags

# restart the web app by touching the WSGI file (depends on the platform)
restart:
	touch hxl-proxy.wsgi

clean:
	rm -rf venv
