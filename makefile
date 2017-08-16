#
# The values of these 3 variables may be overriden by the calling job.
# For instance, BUILD_NUMBER is typically set by the Jenkins job.
#
# Note that BRANCH is only used as modifier in the name of the ARTIFACT; it
# is NOT an actual branch name and MUST be part of a valid file. For instance,
# a value like "support/5.2.x" is NOT valid because it will result in an
# incorrect file name when full value of ARTIFACT is expanded by make.
#
VERSION  ?= 5.3.0
BUILD_NUMBER ?= DEV
BRANCH ?= support-5.3.x

ARTIFACT_TAG ?= $(shell echo $(BRANCH) | sed 's/\//-/g')
ARTIFACT := prodbin-$(VERSION)-$(ARTIFACT_TAG).tar.gz
#
# Use REVISION if you need to do something like a hotfix release.
#
# REVISION ?= 1
# ARTIFACT := prodbin-$(VERSION)-$(REVISION)-$(ARTIFACT_TAG).tar.gz

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
