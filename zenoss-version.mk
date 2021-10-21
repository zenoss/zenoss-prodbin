#
# Makefile for zenoss-version
#

.PHONY: clean-zenoss-version build-zenoss-version

ZENOSS_VERSION_ROOT = legacy/zenoss-version
ZENOSS_VERSION_WHEEL = Zenoss-$(VERSION)-py2-none-any.whl

clean-zenoss-version:
	rm -f $(ZENOSS_VERSION_ROOT)/setup.py
	rm -rf $(ZENOSS_VERSION_ROOT)/src/Zenoss.egg-info
	rm -rf $(ZENOSS_VERSION_ROOT)/build dist

build-zenoss-version: dist/$(ZENOSS_VERSION_WHEEL)

dist/$(ZENOSS_VERSION_WHEEL): $(ZENOSS_VERSION_ROOT)/setup.py | dist
	@echo "Building a binary distribution of zenoss-version"
	$(DOCKER_RUN) "cd /mnt/$(ZENOSS_VERSION_ROOT) && python setup.py bdist_wheel -d /mnt/dist"

$(ZENOSS_VERSION_ROOT)/setup.py: $(ZENOSS_VERSION_ROOT)/setup.py.in
	sed -e 's/%VERSION%/$(VERSION)/g' $< > $@

dist:
	@mkdir -p $@
