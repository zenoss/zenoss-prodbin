#
# Makefile for zenoss-version
#

ZENOSS_VERSION_ROOT = legacy/zenoss-version
ZENOSS_VERSION_WHEEL = Zenoss-$(VERSION)-py2-none-any.whl

.PHONY: clean-zenoss-version build-zenoss-version generate-zmigrateversion

clean-zenoss-version:
	rm -f $(ZENOSS_VERSION_ROOT)/setup.py
	rm -rf $(ZENOSS_VERSION_ROOT)/src/Zenoss.egg-info
	rm -rf $(ZENOSS_VERSION_ROOT)/build dist
	rm -f Products/ZenModel/ZMigrateVersion.py

build-zenoss-version: dist/$(ZENOSS_VERSION_WHEEL)

dist/$(ZENOSS_VERSION_WHEEL): $(ZENOSS_VERSION_ROOT)/setup.py | dist
	@echo "Building a binary distribution of zenoss-version"
	$(DOCKER_RUN) "cd /mnt/$(ZENOSS_VERSION_ROOT) && python setup.py bdist_wheel -d /mnt/dist"

$(ZENOSS_VERSION_ROOT)/setup.py: $(ZENOSS_VERSION_ROOT)/setup.py.in
	sed -e 's/%VERSION%/$(VERSION)/g' $< > $@

dist:
	@mkdir -p $@


# The SCHEMA_* values define the DB schema version used for upgrades.
# See the topic "Managing Migrate.Version" in Products/ZenModel/migrate/README.md
# for more information about setting these values.

pick_version_part = $(word $(1),$(subst ., ,$(2)))

SCHEMA_VERSION  = $(shell cat SCHEMA_VERSION)
SCHEMA_MAJOR    = $(call pick_version_part,1,$(SCHEMA_VERSION))
SCHEMA_MINOR    = $(call pick_version_part,2,$(SCHEMA_VERSION))
SCHEMA_REVISION = $(call pick_version_part,3,$(SCHEMA_VERSION))

# Exists for backward compatibility
generate-zversion: generate-zmigrateversion

# See the topic "Managing Migrate.Version" in Products/ZenModel/migrate/README.md
# for more information about setting the SCHEMA_* values.
generate-zmigrateversion: Products/ZenModel/ZMigrateVersion.py

Products/ZenModel/ZMigrateVersion.py: Products/ZenModel/ZMigrateVersion.py.in SCHEMA_VERSION
	sed \
		-e 's/%SCHEMA_MAJOR%/$(SCHEMA_MAJOR)/g' \
		-e 's/%SCHEMA_MINOR%/$(SCHEMA_MINOR)/g' \
		-e 's/%SCHEMA_REVISION%/$(SCHEMA_REVISION)/g' \
		$< > $@

# The target replace-zmigrationversion should be used just prior to release to lock
# down the schema versions for a particular release
replace-zmigrateversion:
	@echo Replacing SCHEMA_MAJOR with $(SCHEMA_MAJOR)
	@echo Replacing SCHEMA_MINOR with $(SCHEMA_MINOR)
	@echo Replacing SCHEMA_REVISION with $(SCHEMA_REVISION)
	@cd Products/ZenModel/migrate; \
		for file in `grep -l ZMigrateVersion *.py`; do \
		    sed \
			    -e "/ZMigrateVersion/d" \
				-e "s/SCHEMA_MAJOR/$(SCHEMA_MAJOR)/g;s/SCHEMA_MINOR/$(SCHEMA_MINOR)/g;s/SCHEMA_REVISION/$(SCHEMA_REVISION)/g" \
				$$file; \
		done

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
