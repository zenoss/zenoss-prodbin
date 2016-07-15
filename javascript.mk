#
# Makefile for Zenoss Javascript files
#
# Approximately 100+ individaul zenoss javascript files are compressed into
# a single 'minified' file using a Sencha tool called JSBuilder. The
# minification process is orchestrated by a json-structured jsb2 build
# file:
#
#                                                +--------------+
# Products/ZenUI3/browser/zenoss.jsb2 ---------->|    sencha    |
# Products/ZenUI3/browser/resources/js/*/*.js -->|   minifier   |-->zenoss-compiled.js
#                                                |--------------|
#                                                |JSBuilder2.jar|
#                                                +--------------+
#
# The jsb2 file defines the output file (e.g. zenoss-compiled.js) and the
# output directory (e.g. resources/js/deploy), so we parse the jsb2 file to
# get those settings.
#---------------------------------------------------------------------------#

ZENOSS_JS_BASEDIR   := Products/ZenUI3/browser
ZENOSS_JSB_FILE     := $(ZENOSS_JS_BASEDIR)/zenoss.jsb2
ZENOSS_SRC_BASEDIR  := $(ZENOSS_JS_BASEDIR)/resources/js

#
# JSB_COMPILED_JS_NAME - the output filename from the jsb2 file; e.g. "zenoss-compiled.js"
#
JSB_COMPILED_JS_NAME = $(shell grep '"file":' $(ZENOSS_JSB_FILE) | awk '{print $$2}' | tr -d [\",])

#
# JSB_DEPLOY_DIR - the output directory name from the jsb2 file; e.g. "resources/js/deploy"
#
JSB_DEPLOY_DIR = $(shell grep '"deployDir":' $(ZENOSS_JSB_FILE) | awk '{print $$2}' | tr -d [\",])

#
# JS_OUTPUT_DIR - the output directory relative to the repo root; e.g. Products/ZenUI3/browser/resources/js/deploy
#
JS_OUTPUT_DIR = $(ZENOSS_JS_BASEDIR)/$(JSB_DEPLOY_DIR)

# JSBUILDER - the path to the JSBuilder jar in the runtime image
JSBUILDER = /opt/zenoss/share/java/sencha_jsbuilder-2/JSBuilder2.jar

# Define the name, version and tag name for the docker build image
# Note that build-tools is derived from zenoss-centos-base which contains JSBuilder
BUILD_IMAGE = build-tools
BUILD_VERSION = 0.0.3
BUILD_IMAGE_TAG = zenoss/$(BUILD_IMAGE):$(BUILD_VERSION)

UID := $(shell id -u)
GID := $(shell id -g)

.PHONY: clean build

clean:
	-rm -rf $(JS_OUTPUT_DIR)

build:
	@echo "Minifying $(ZENOSS_SRC_BASEDIR) -> $(JS_OUTPUT_DIR)/$(JSB_COMPILED_JS_NAME)"
	docker run --rm \
		-v $(PWD):/mnt \
		--user $(UID):$(GID) \
		$(BUILD_IMAGE_TAG) \
		/bin/bash -c "cd /mnt && java -jar $(JSBUILDER) -p $(ZENOSS_JSB_FILE) -d $(ZENOSS_JS_BASEDIR) -v"
