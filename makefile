VERSION = $(shell cat VERSION)

BUILD_NUMBER ?= DEV
BRANCH       ?= support/6.x
ARTIFACT_TAG ?= $(shell echo $(BRANCH) | sed 's/\//-/g')
ARTIFACT     := prodbin-$(VERSION)-$(ARTIFACT_TAG).tar.gz

# Define the name, version and tag name for the docker build image
# Note that build-tools is derived from zenoss-centos-base which contains JSBuilder
BUILD_IMAGE = build-tools
BUILD_VERSION = 0.0.11
BUILD_IMAGE_TAG = zenoss/$(BUILD_IMAGE):$(BUILD_VERSION)

USER_ID := $(shell id -u)
GROUP_ID := $(shell id -g)

DOCKER_RUN := docker run --rm \
	-v $(PWD):/mnt \
	--user $(USER_ID):$(GROUP_ID) \
	$(BUILD_IMAGE_TAG) \
	/bin/bash -c

.PHONY: all clean build

all: build

include javascript.mk
include zenoss-version.mk

#
# To build the tar,
#     - create the 'dist' subdirectory
#     - compile & minify the javascript, which is saved in the Products directory tree
#     - build the zenoss-version wheel, which is copied into dist

EXCLUSIONS=--exclude Products/ZenModel/ZMigrateVersion.py.in
INCLUSIONS=Products bin dist etc share legacy/sitecustomize.py

build: build-javascript build-zenoss-version Products/ZenModel/ZMigrateVersion.py
	tar cvfz $(ARTIFACT) $(EXCLUSIONS) $(INCLUSIONS)

clean: clean-javascript clean-zenoss-version
	rm -f $(ARTIFACT)
