VERSION  ?= 7.0.17
BUILD_NUMBER ?= DEV
BRANCH   ?= develop
ARTIFACT_TAG ?= $(shell echo $(BRANCH) | sed 's/\//-/g')
ARTIFACT := prodbin-$(VERSION)-$(ARTIFACT_TAG).tar.gz

# The SCHEMA_* values define the DB schema version used for upgrades.
# See the topic "Managing Migrate.Version" in Products/ZenModel/migrate/README.md
# for more information about setting these values.
# See zenoss-version.mk for more information about make targets that use these values.
SCHEMA_MAJOR ?= 300
SCHEMA_MINOR ?= 0 
SCHEMA_REVISION ?= 14

DIST_ROOT := dist

# Define the name, version and tag name for the docker build image
# Note that build-tools is derived from zenoss-centos-base which contains JSBuilder
BUILD_IMAGE = build-tools
BUILD_VERSION = 0.0.11
BUILD_IMAGE_TAG = zenoss/$(BUILD_IMAGE):$(BUILD_VERSION)

UID := $(shell id -u)
GID := $(shell id -g)

DOCKER_RUN := docker run --rm \
		-v $(PWD):/mnt \
		--user $(UID):$(GID) \
		$(BUILD_IMAGE_TAG) \
		/bin/bash -c

.PHONY: all clean build javascript

include javascript.mk
include zenoss-version.mk

all: build

mk-dist:
	mkdir -p $(DIST_ROOT)

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
	rm -rf $(DIST_ROOT)
#
