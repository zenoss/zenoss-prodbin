VERSION       = $(shell cat VERSION)
BRANCH       ?= $(shell git rev-parse --abbrev-ref HEAD)
ARTIFACT_TAG ?= $(shell echo $(BRANCH) | sed 's/\//-/g')
ARTIFACT      = prodbin-$(VERSION)-$(ARTIFACT_TAG).tar.gz

IMAGE = zenoss/zenoss-centos-base:1.4.0.devtools

USER_ID := $(shell id -u)
GROUP_ID := $(shell id -g)

DOCKER = $(shell which docker 2>/dev/null)
ifneq ($(DOCKER),)
_common_cmd = $(DOCKER) run --rm -v $(PWD):/mnt -w /mnt
DOCKER_USER = $(_common_cmd) --user $(USER_ID):$(GROUP_ID) $(IMAGE)
DOCKER_ROOT = $(_common_cmd) $(IMAGE)
endif

ZENHOME = $(shell echo $$ZENHOME)

.PHONY: default test clean build javascript build-javascript

default: $(ARTIFACT)

include javascript.mk
include migration.mk

EXCLUSIONS = *.pyc $(MIGRATE_VERSION).in Products/ZenModel/migrate/tests Products/ZenUITests

ARCHIVE_EXCLUSIONS = $(foreach item,$(EXCLUSIONS),--exclude=$(item))
ARCHIVE_INCLUSIONS = Products bin lib etc share Zenoss.egg-info

build: $(ARTIFACT)

# equivalent to python setup.py develop
install: setup.py $(JSB_TARGETS) $(MIGRATE_VERSION)
ifeq ($(ZENHOME),/opt/zenoss)
	@python setup.py develop
else
	@echo "Please execute this target in a devshell container (where ZENHOME=/opt/zenoss)."
endif

clean: clean-javascript clean-migration
	rm -f $(ARTIFACT) install-zenoss.mk
	rm -rf Zenoss.egg-info lib

$(ARTIFACT): $(JSB_TARGETS) $(MIGRATE_VERSION) Zenoss.egg-info
	tar cvfz $@ $(ARCHIVE_EXCLUSIONS) $(ARCHIVE_INCLUSIONS)

Zenoss.egg-info: install-zenoss.mk setup.py
ifneq ($(DOCKER),)
	$(DOCKER_ROOT) make -f install-zenoss.mk install
else
	$(error The $@ target requires Docker)
endif

install-zenoss.mk: install-zenoss.mk.in
	sed -e "s/%GID%/$(GROUP_ID)/" -e "s/%UID%/$(USER_ID)/" $< > $@
