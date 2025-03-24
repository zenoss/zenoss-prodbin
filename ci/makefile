VERSION = $(shell cat ../VERSION)
ZENOSS_UID = $(shell id -u)
ZENOSS_GID = $(shell id -g)

DOCKERFILE = prodbin/Dockerfile

# The location of the product-assembly repo will vary depending
# on where this makefile runs.  In a zendev environment, it'll
# be a sibling directory with zenoss-prodbin.  On a Jenkins node,
# it'll be a subdirectory of zenoss-prodbin.
ASSEMBLY_PATH = $(shell find ../ -name product-assembly -type d)
ifeq ($(ASSEMBLY_PATH),)
ASSEMBLY_PATH = ../../product-assembly
endif

# Returns the component name, e.g. ctx/components/phantomjs.tar.bz2 -> phantomjs
get_component_name = $(subst .tar,,$(subst -0-py2-none-any,,$(notdir $(basename $(1)))))

COMPONENTS_DIR = prodbin/components
COMPONENT_FILES = \
	extjs.tgz \
	modelindex.tgz \
	libsmi.deb \
	penparser-0-py2-none-any.whl \
	pydeps.tgz \
	pynetsnmp-0-py2-none-any.whl \
	service-migration-0-py2-none-any.whl \
	zenoss.protocols-0-py2-none-any.whl \
	zenoss.toolbox-0-py2-none-any.whl \
	zensocket.tgz
COMPONENTS = $(addprefix $(COMPONENTS_DIR)/,$(COMPONENT_FILES))
COMPONENT_VERSIONS = $(ASSEMBLY_PATH)/component_versions.json
MODELINDEX_WHL = $(COMPONENTS_DIR)/zenoss.modelindex-0-py2-none-any.whl

ZENOSS_WHL = $(COMPONENTS_DIR)/zenoss-0-py2-none-any.whl
ZENOSS_SRC = $(shell ls -t ../dist/*.whl | head -1)

PYTHON_PATCHES_SRC = $(wildcard $(ASSEMBLY_PATH)/product-base/python_patches/*)
PYTHON_PATCH_FILES = $(subst $(ASSEMBLY_PATH)/product-base/,,$(PYTHON_PATCHES_SRC))
PYTHON_PATCHES = $(addprefix prodbin/,$(PYTHON_PATCH_FILES))

SOLR_FILENAMES = schema.xml solrconfig.xml
SOLR_TAR_PATH = zenoss/modelindex/solr/configsets/zenoss_model/conf
SOLR_FILES_DIR = solr/zenoss_model/conf
SOLR_FILES = $(addprefix $(SOLR_FILES_DIR)/,$(SOLR_FILENAMES))

DEPENDENCIES = \
	$(DOCKERFILE) \
	mariadb/initdb.d/zodb.sql.gz \
	$(COMPONENTS) \
	$(MODELINDEX_WHL) \
	$(ZENOSS_WHL) \
	$(SOLR_FILES) \
	prodbin/hubpasswd \
	prodbin/sitecustomize.py \
	prodbin/ZENOSS-MIB.txt \
	$(PYTHON_PATCHES)

.DEFAULT_GOAL := test

.PHONY: test
test: deps
	@docker compose down
	@docker compose up --remove-orphans --build --attach runtests --exit-code-from runtests; code=$$?; docker compose down; exit $$code

# Target to setup dependencies for running tests
.PHONY: deps
deps: $(DEPENDENCIES)

mariadb/initdb.d $(COMPONENTS_DIR) prodbin/python_patches $(SOLR_FILES_DIR):
	@mkdir -p $@

prodbin/hubpasswd prodbin/sitecustomize.py: prodbin/%: $(ASSEMBLY_PATH)/product-base/%
	@cp $< $@

prodbin/ZENOSS-MIB.txt: $(ASSEMBLY_PATH)/product-base/share/mibs/site/ZENOSS-MIB.txt
	@cp $< $@

$(DOCKERFILE): $(DOCKERFILE).in prodbin/packages.txt ../VERSION
	@cat $< | sed \
		-e 's|%PACKAGES%|$(shell cat prodbin/packages.txt)|' \
		-e 's|%VERSION%|$(VERSION)|' \
		-e 's|%GID%|$(ZENOSS_GID)|' \
		-e 's|%UID%|$(ZENOSS_UID)|' \
		- > $@

$(SOLR_FILES): $(COMPONENTS_DIR)/modelindex.tgz | $(SOLR_FILES_DIR)
	@tar xf $< -C $(SOLR_FILES_DIR)/ --strip-components=6 $(addprefix $(SOLR_TAR_PATH)/,$(notdir $@))

mariadb/initdb.d/zodb.sql.gz: | mariadb/initdb.d
mariadb/initdb.d/zodb.sql.gz: ../src/Products/ZenModel/data/zodb.sql.gz
	@cp $< $@

$(MODELINDEX_WHL): $(COMPONENTS_DIR)/modelindex.tgz
	@tar -xz -C $(COMPONENTS_DIR)/ -f $< --strip-components=1 --wildcards --transform="s/-[0-9.]\+-/-0-/" dist/zenoss.modelindex*.whl

$(ZENOSS_WHL): $(ZENOSS_SRC)
	@cp $< $@

$(COMPONENTS): $(COMPONENT_VERSIONS) | $(COMPONENTS_DIR)
$(COMPONENTS): $(COMPONENTS_DIR)/%:
	@$(ASSEMBLY_PATH)/zat get --name $@ $< $(call get_component_name,$@)

$(PYTHON_PATCHES): | prodbin/python_patches
$(PYTHON_PATCHES): prodbin/%: $(ASSEMBLY_PATH)/product-base/%
	@cp $< $@
