#
# Makefile for zenoss-version
#

# The SCHEMA_* values define the DB schema version used for upgrades.
# See the topic "Managing Migrate.Version" in Products/ZenModel/migrate/README.md
# for more information about setting these values.
subver = $(word $2,$(subst ., ,$1))
SCHEMA_VERSION := $(shell cat SCHEMA_VERSION)
SCHEMA_MAJOR ?= $(call subver,$(SCHEMA_VERSION),1)
SCHEMA_MINOR ?= $(call subver,$(SCHEMA_VERSION),2)
SCHEMA_REVISION ?= $(call subver,$(SCHEMA_VERSION),3)

VERSION_TARGET = Products/ZenModel/ZVersion.py
VERSION_SCHEMA_TARGET = Products/ZenModel/ZMigrateVersion.py

.PHONY: clean-zenoss-version generate-zversion generate-zmigrateversion replace-zmigrateversion verify-explicit-zmigrateversion

$(VERSION_TARGET): $(VERSION_TARGET).in VERSION
	@echo "generating ZVersion.py"
	sed -e 's/%VERSION_STRING%/$(VERSION)/g; s/%BUILD_NUMBER%/$(BUILD_NUMBER)/g' $< > $@

SED_SCHEMA_REGEX := "\
    s/%SCHEMA_MAJOR%/$(SCHEMA_MAJOR)/g; \
    s/%SCHEMA_MINOR%/$(SCHEMA_MINOR)/g; \
    s/%SCHEMA_REVISION%/$(SCHEMA_REVISION)/g;"

# See the topic "Managing Migrate.Version" in Products/ZenModel/migrate/README.md
# for more information about setting these SCHEMA_* values.
$(VERSION_SCHEMA_TARGET): $(VERSION_SCHEMA_TARGET).in SCHEMA_VERSION
	@echo "generating ZMigrateVersion.py"
	sed -e $(SED_SCHEMA_REGEX) $< > $@

# Build targets for generating the versioned Python modules
generate-zversion: generate-zmigrateversion $(VERSION_TARGET)
generate-zmigrateversion: $(VERSION_SCHEMA_TARGET)

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

clean-zenoss-version:
	rm -f $(VERSION_SCHEMA_TARGET) $(VERSION_TARGET)
