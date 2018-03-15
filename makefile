VERSION  ?= 6.1.3
BUILD_NUMBER ?= DEV
BRANCH   ?= support-6.1.x
ARTIFACT_TAG ?= $(shell echo $(BRANCH) | sed 's/\//-/g')
ARTIFACT := prodbin-$(VERSION)-$(ARTIFACT_TAG).tar.gz

# The SCHEMA_* values define the DB schema version used for upgrades.
# See the topic "Managing Migrate.Version" in Products/ZenModel/migrate/README.md
# for more information about setting these values.
# See zenoss-version.mk for more information about make targets that use these values.
SCHEMA_MAJOR ?= 200
SCHEMA_MINOR ?= 1
SCHEMA_REVISION ?= 2

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
#
