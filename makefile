VERSION  ?= 5.2.0
BUILD_NUMBER ?= DEV
BRANCH   ?= develop
REVISION ?= 3
ARTIFACT := prodbin-$(VERSION)-$(REVISION)-$(BRANCH).tar.gz

DIST_ROOT := dist

# Define the name, version and tag name for the docker build image
# Note that build-tools is derived from zenoss-centos-base which contains JSBuilder
BUILD_IMAGE = build-tools
BUILD_VERSION = 0.0.5
BUILD_IMAGE_TAG = zenoss/$(BUILD_IMAGE):$(BUILD_VERSION)

UID := $(shell id -u)
GID := $(shell id -g)

DOCKER_RUN := docker run --rm \
		-v $(PWD):/mnt \
		--user $(UID):$(GID) \
		$(BUILD_IMAGE_TAG) \
		/bin/bash -c

.PHONY: all clean build javascript zensocket

include javascript.mk
include zensocket.mk
include zenoss-version.mk

all: build

mk-dist:
	mkdir -p $(DIST_ROOT)

#
# To build the tar,
#     - create the 'dist' subdirectory
#     - compile & minify the javascript, which is saved in the Products directory tree
#     - compile the zensocket binary, which is copied into bin
#     - build the zenoss-version wheel, which is copied into dist
#
build: mk-dist build-javascript build-zensocket build-zenoss-version
	tar cvfz $(ARTIFACT) Products bin dist etc share legacy/sitecustomize.py

clean: clean-javascript clean-zensocket clean-zenoss-version
	rm -f $(ARTIFACT)
	rm -rf $(DIST_ROOT)
