VERSION      ?= $(shell cat VERSION)
BUILD_NUMBER ?= DEV
BRANCH       ?= develop
ARTIFACT_TAG ?= $(shell echo $(BRANCH) | sed 's/\//-/g')
ARTIFACT     := prodbin-$(VERSION)-$(ARTIFACT_TAG).tar.gz

# Define the name, version and tag name for the docker build image
# Note that build-tools is derived from zenoss-centos-base which contains JSBuilder
BUILD_IMAGE = build-tools
BUILD_VERSION = 0.0.11
BUILD_IMAGE_TAG = zenoss/$(BUILD_IMAGE):$(BUILD_VERSION)

UID := $(shell id -u)
GID := $(shell id -g)

DOCKER = $(shell which docker 2>/dev/null)

DOCKER_RUN := docker run --rm \
		-v $(PWD):/mnt \
		-w /mnt \
		--user $(UID):$(GID) \
		$(BUILD_IMAGE_TAG) \
		/bin/bash -c

.PHONY: all test clean build javascript zensocket

default: build

test:
	$(DOCKER_RUN) "make build-javascript"

#
# To build the tar,
#     - compile & minify the javascript, which is saved in the Products directory tree
#     - compile the zensocket binary, which is copied into bin
#
# build: setup.py build-javascript build-zensocket generate-zversion
# 	python setup.py bdist_wheel
build: $(ARTIFACT)
	@echo $< built.

ARTIFACT_INCLUSIONS = Products bin etc share legacy/sitecustomize.py setup.py

$(ARTIFACT): setup.py build-javascript build-zensocket generate-zversion
	@tar cvzf $(ARTIFACT) $(ARTIFACT_INCLUSIONS)

setup.py: setup.py.in VERSION
	@sed -e "s/%VERSION%/$(VERSION)/g" $< > $@

# equivalent to python setup.py develop
install: setup.py build-javascript build-zensocket generate-zversion
	@pip install -e ./

clean: clean-javascript clean-zensocket clean-zenoss-version
	@rm -f $(ARTIFACT) setup.py
	@rm -rf Zenoss.egg-info

include javascript.mk
include zensocket.mk
include zenoss-version.mk
