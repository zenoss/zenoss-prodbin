#
# Makefile for zenoss-version
#
.PHONY: clean-zenoss-version build-zenoss-version pkg-zenoss-version generate-zversion

ZENOSS_VERSION_BASE := legacy/zenoss-version
WHEEL_ARTIFACT := $(ZENOSS_VERSION_BASE)/dist/Zenoss-$(VERSION)-py2-none-any.whl

clean-zenoss-version:
	rm -f $(ZENOSS_VERSION_BASE)/setup.py
	rm -rf $(ZENOSS_VERSION_BASE)/src/Zenoss.egg-info
	rm -rf $(ZENOSS_VERSION_BASE)/build $(ZENOSS_VERSION_BASE)/dist
	rm -f Products/ZenModel/ZMigrateVersion.py

build-zenoss-version: mk-dist $(WHEEL_ARTIFACT)
	cp $(WHEEL_ARTIFACT) $(DIST_ROOT)

$(WHEEL_ARTIFACT): build-version-wheel

build-version-wheel: generate-zversion
	@echo "Building a binary distribution of zenoss-version"
	sed -e 's/%VERSION%/$(VERSION)/g' $(ZENOSS_VERSION_BASE)/setup.py.in > $(ZENOSS_VERSION_BASE)/setup.py
	$(DOCKER_RUN) "cd /mnt/$(ZENOSS_VERSION_BASE) && python setup.py bdist_wheel"

generate-zversion: generate-zmigrateversion
	@echo "generating ZVersion.py"
	sed -e 's/%VERSION_STRING%/$(VERSION)/g; s/%BUILD_NUMBER%/$(BUILD_NUMBER)/g' Products/ZenModel/ZVersion.py.in > Products/ZenModel/ZVersion.py

SED_SCHEMA_REGEX := "\
    s/%SCHEMA_MAJOR%/$(SCHEMA_MAJOR)/g; \
    s/%SCHEMA_MINOR%/$(SCHEMA_MINOR)/g; \
    s/%SCHEMA_REVISION%/$(SCHEMA_REVISION)/g;"

# See the topic "Managing Migrate.Version" in Products/ZenModel/migrate/README.md
# for more information about setting these SCHEMA_* values.
generate-zmigrateversion:
	@echo "generating ZMigrateVersion.py"
	sed -e $(SED_SCHEMA_REGEX) Products/ZenModel/ZMigrateVersion.py.in > Products/ZenModel/ZMigrateVersion.py

# The target replace-zmigrationversion should be used just prior to release to lock
# down the schema versions for a particular release
replace-zmigrateversion:
	SCHEMA_MAJOR=$(SCHEMA_MAJOR) SCHEMA_MINOR=$(SCHEMA_MINOR) SCHEMA_REVISION=$(SCHEMA_REVISION) ./replace-zmigrateversion.sh

SCHEMA_FOUND = $(shell grep Migrate.Version Products/ZenModel/migrate/*.py  | grep SCHEMA_)

# The target verify-explicit-zmigrateversion should be invoked as a first step in all release
# builds to verify that all of the SCHEMA_* variables were replaced with an actual numeric value.
verify-explicit-zmigrateversion:
ifeq ($(SCHEMA_FOUND),)
	@echo "Good - no SCHEMA_* variables found: $(SCHEMA_FOUND)"
else
	$(info grep for SCHEMA_ in Products/ZenModel/migrate/*.py found:)
	$(info $(SCHEMA_FOUND))
	$(error At least one of the SCHEMA_* variables found)
endif

