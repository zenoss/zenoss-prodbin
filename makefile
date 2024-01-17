VERSION       = $(shell cat VERSION)
BRANCH       ?= $(shell git rev-parse --abbrev-ref HEAD)
ARTIFACT_TAG ?= $(shell echo $(BRANCH) | sed 's/\//-/g')
ARTIFACT      = prodbin-$(VERSION)-$(ARTIFACT_TAG).tar.gz

IMAGE = zenoss/zenpackbuild:ubuntu2204-5

ZENHOME = $(shell echo $$ZENHOME)

.DEFAULT_GOAL := $(ARTIFACT)

include javascript.mk
include migration.mk

EXCLUSIONS = *.pyc $(MIGRATE_VERSION).in Products/ZenModel/migrate/tests Products/ZenUITests

ARCHIVE_EXCLUSIONS = $(foreach item,$(EXCLUSIONS),--exclude=$(item))
ARCHIVE_INCLUSIONS = Products bin etc share VERSION setup.py

.PHONY: build
build: $(ARTIFACT)

# equivalent to python setup.py develop
.PHONY: install
install: setup.py $(JSB_TARGETS) $(MIGRATE_VERSION)
ifeq ($(ZENHOME),/opt/zenoss)
	@pip install --prefix /opt/zenoss -e .
else
	@echo "Please execute this target in a devshell container (where ZENHOME=/opt/zenoss)."
endif

.PHONY: clean
clean: clean-javascript clean-migration
	rm -f $(ARTIFACT)

$(ARTIFACT): $(JSB_TARGETS) $(MIGRATE_VERSION) VERSION setup.py
	tar cvfz $@ $(ARCHIVE_EXCLUSIONS) $(ARCHIVE_INCLUSIONS)
