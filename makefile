VERSION = $(shell cat VERSION)

BUILD_NUMBER ?= DEV
BRANCH       ?= develop
ARTIFACT_TAG ?= $(shell echo $(BRANCH) | sed 's/\//-/g')
ARTIFACT     := prodbin-$(VERSION)-$(ARTIFACT_TAG).tar.gz

IMAGE = zenoss/zenoss-centos-base:1.3.4.devtools

USER_ID := $(shell id -u)
GROUP_ID := $(shell id -g)

DOCKER = $(shell which docker)

DOCKER_RUN = $(DOCKER) run --rm -v $(PWD):/mnt -w /mnt --user $(USER_ID):$(GROUP_ID) $(IMAGE) /bin/bash -c

.PHONY: all clean build

all: build

include javascript.mk
include migration.mk
include zenoss-version.mk

#
# To build the tar,
#     - create the 'dist' subdirectory
#     - compile & minify the javascript, which is saved in the Products directory tree
#     - build the zenoss-version wheel, which is copied into dist

EXCLUSIONS = *.pyc $(MIGRATE_VERSION).in Products/ZenModel/migrate/tests Products/ZenUITests

ARCHIVE_EXCLUSIONS = $(foreach item,$(EXCLUSIONS),--exclude=$(item))
ARCHIVE_INCLUSIONS = Products bin dist etc share

build: $(ARTIFACT)

clean: clean-javascript clean-migration clean-zenoss-version
	rm -f $(ARTIFACT)

$(ARTIFACT): $(JSB_TARGETS) $(MIGRATE_VERSION) dist/$(ZENOSS_VERSION_WHEEL)
	tar cvfz $@ $(ARCHIVE_EXCLUSIONS) $(ARCHIVE_INCLUSIONS)
