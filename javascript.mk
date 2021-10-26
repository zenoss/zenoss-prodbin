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

JS_BASEDIR     = Products/ZenUI3/browser
JSB_FILE       = $(JS_BASEDIR)/zenoss.jsb2
JS_SRC_BASEDIR = $(JS_BASEDIR)/resources/js

#
# JSB_COMPILED_JS_NAME - the output filename from the jsb2 file; e.g. "zenoss-compiled.js"
#
JSB_COMPILED_JS_NAME = $(shell grep '"file":' $(JSB_FILE) | awk '{print $$2}' | tr -d [\",])

#
# JSB_DEPLOY_DIR - the output directory name from the jsb2 file; e.g. "resources/js/deploy"
#
JSB_DEPLOY_DIR = $(shell grep '"deployDir":' $(JSB_FILE) | awk '{print $$2}' | tr -d [\",])

#
# JS_OUTPUT_DIR - the output directory relative to the repo root;
# e.g. Products/ZenUI3/browser/resources/js/deploy
#
JS_OUTPUT_DIR = $(JS_BASEDIR)/$(JSB_DEPLOY_DIR)

# JSBUILDER - the path to the JSBuilder jar in the runtime image
JSBUILDER = /opt/zenoss/share/java/sencha_jsbuilder-2/JSBuilder2.jar

JSBUILD_COMMAND = java -jar $(JSBUILDER) -p $(JSB_FILE) -d $(JS_BASEDIR) -v

# Dependencies for compilation
JSB_SOURCES = $(shell python2 -c "import json, sys, os.path; d=sys.stdin.read(); p=json.loads(d)['pkgs'][0]['fileIncludes']; print ' '.join(os.path.join('$(JS_BASEDIR)', e['path'], e['text']) for e in p)" < $(JSB_FILE))
JSB_TARGETS = $(JS_OUTPUT_DIR)/zenoss-compiled.js $(JS_OUTPUT_DIR)/zenoss-compiled-debug.js

.PHONY: clean-javascript build-javascript

build-javascript: $(JSB_TARGETS)

clean-javascript:
	@-rm -vrf $(JS_OUTPUT_DIR)

$(JSB_TARGETS): $(JSB_SOURCES)
	@echo "Minifying $(JS_SRC_BASEDIR) -> $@"
ifeq ($(DOCKER),)
	$(JSBUILD_COMMAND)
else
	$(DOCKER_RUN) "cd /mnt && $(JSBUILD_COMMAND)"
endif
