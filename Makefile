########################################################################
# Makefile to automate common tasks
#
# build-venv - (re)build the Python virtual environment if needed
# test - run the unit tests
# test-failed - rerun just the failed unit tests
# test-install - test a fresh installation in a temporary venv
# test-docker - test a docker build
# run-local - launch a temporary local server
# browser-tests-local - run in-browser tests on the local server
# browser-tests-dev - run browser tests on the dev server
# browser-tests-staging - run browser tests on the staging server
# browser-tests-prod - run browser tests on the production server
# publish-pypi - publish a new release to PyPi
# tags - build an Emacs TAGS file
########################################################################


# activation script for the Python virtual environment
VENV=venv/bin/activate

PYTEST_OPTS=-W ignore::DeprecationWarning
PIP3_OPTS=-q
PYTHON_OPTS=-W ignore:::pkg_resources # get rid of the deprecation warnings
SETUP_OPTS=-q

all: $(VENV)

# (re)build the virtual environment if it's missing, or whenever setup.cfg changes
$(VENV): setup.cfg requirements.txt
	rm -rf venv
	python3 -m venv venv
	. $(VENV) && python3 ${PYTHON_OPTS} setup.py ${SETUP_OPTS} develop

# run unit tests
test: $(VENV)
	. $(VENV) && pytest ${PYTEST_OPTS}

# run failed unit tests
test-failed: $(VENV)
	. $(VENV) && pytest ${PYTEST_OPTS} --lf

# alias to (re)build the Python virtual environment
build-venv: $(VENV)

# do a cold install in a temporary virtual environment and run unit tests
test-install:
	pip3 ${PIP3_OPTS} cache remove '*'
	echo "Testing setup.py ..."
	rm -rf venv-test
	python3 -m venv venv-test
	. venv-test/bin/activate && python3 ${PYTHON_OPTS} setup.py ${SETUP_OPTS} install && pytest ${PYTEST_OPTS}
	echo "Testing requirements.txt ..."
	rm -rf venv-test
	python3 -m venv venv-test
	. venv-test/bin/activate && pip3 ${PIP3_OPTS} install -r requirements.txt && pytest ${PYTEST_OPTS}
	rm -rf venv-test # make sure we clean up

# Add target for docker build
test-docker:
	pkexec docker build --no-cache -t "unocha/hxl-proxy:local" `pwd`

# run local dev (needs config in local/config.py)
run-local: $(VENV)
	. $(VENV) && HXL_PROXY_CONFIG=../local/config.py flask --app hxl_proxy run

debug-local: $(VENV)
	. $(VENV) && HXL_PROXY_CONFIG=../local/config.py flask --debug --app hxl_proxy run

# browser tests for dev.proxy.hxlstandard.org
browser-tests-local:
	cat tests/browser-tests/local-urls.txt | xargs -d '\n' firefox

# browser tests for dev.proxy-hxlstandard-org.ahconu.org
browser-tests-dev:
	cat tests/browser-tests/dev-urls.txt | xargs -d '\n' firefox

# browser tests for stage.proxy-hxlstandard-org.ahconu.org
browser-tests-staging:
	cat tests/browser-tests/staging-urls.txt | xargs -d '\n' firefox

# browser tests for proxy.hxlstandard.org
browser-tests-prod:
	cat tests/browser-tests/prod-urls.txt | xargs -d '\n' firefox

# publish a new release on PyPi
publish-pypi: $(VENV)
	rm -rf dist/*
	. $(VENV) \
	  && pip3 ${PIP3_OPTS} -q install twine \
	  && python3 ${PYTHON_OPTS} setup.py ${SETUP_OPTS} sdist \
	  && twine upload dist/*

# (re)generate emacs TAGS file
tags:
	find hxl_proxy tests -name '*.py' -o -name '*.csv' -o -name '*.html' -o -name '*.j2' -o -name '*.js' \
	  | grep -v static/jquery \
	  | grep -v static/bootstrap \
	  | grep -v static/compat \
	  | xargs etags

clean:
	rm -rf venv
