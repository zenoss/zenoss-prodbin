#============================================================================
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
#============================================================================
.DEFAULT_GOAL := help # all|build|clean|distclean|devinstall|install|help
.SUFFIXES:
MAKEFLAGS += -r

#============================================================================
# Build component configuration.
#
# Beware of trailing spaces.
# Don't let your editor turn tabs into spaces or vice versa.
#============================================================================
COMPONENT              = bin
COMPONENT_OWNER       ?= $(USER)
COMPONENT_GROUP       ?= $(USER)
BIN_TYPES              = ascii bash dosbat python shell
USE_MANIFEST_SRC      ?= no
SRC_DIR                = .
BUILD_TOP              = build
COMPONENT_PREFIX       = install/bin


# Normalize src dir by adding trailing slash.
_SRC_DIR              := $(shell echo $(strip $(SRC_DIR)) | sed -e "s|\([^\/]\)$$|\1\/|g")
ifeq "$(USE_MANIFEST_SRC)" "yes"
BUILD_DIR              = $(BUILD_TOP)/manifest
else
BUILD_DIR              = $(BUILD_TOP)/discovered
endif
ABS_BUILD_DIR         := $(abspath $(BUILD_DIR))
ABS_SRC_DIR           := $(abspath $(_SRC_DIR))
DISCOVERED_SRC_EXT    := discovered
MANIFEST_SRC_EXT      := manifest
META_SRC               = GNUmakefile|zenmagic.mk|.*.mk|$(COMPONENT).log|\.git.*|\.svn.*|.*.$(DISCOVERED_SRC_EXT)|.checked.*|.*.$(MANIFEST_SRC_EXT)|.*\.log
#
bash_EXCLUDE_FILTER   := $(META_SRC)
bash_INCLUDE_FILTER   := bash|bourne.*again
bash_MAGIC            := /bin/bash
bash_PERMS             = $(EXEC_FILE_PERMS)
bash_OWNER            ?= $(COMPONENT_OWNER)
bash_GROUP            ?= $(COMPONENT_GROUP)
#
dosbat_EXCLUDE_FILTER := $(META_SRC)
dosbat_INCLUDE_FILTER := dos batch
dosbat_PERMS           = $(EXEC_FILE_PERMS)
dosbat_OWNER          ?= $(COMPONENT_OWNER)
dosbat_GROUP          ?= $(COMPONENT_GROUP)
#
python_EXCLUDE_FILTER := $(META_SRC)
python_INCLUDE_FILTER := python
python_MAGIC          := /usr/bin/env python
python_PERMS           = $(EXEC_FILE_PERMS)
python_OWNER          ?= $(COMPONENT_OWNER)
python_GROUP          ?= $(COMPONENT_GROUP)
#
shell_EXCLUDE_FILTER  := $(META_SRC)|bash|bourne.*again
shell_INCLUDE_FILTER  := shell script
shell_MAGIC           := /bin/sh
shell_PERMS            = $(EXEC_FILE_PERMS)
shell_OWNER           ?= $(COMPONENT_OWNER)
shell_GROUP           ?= $(COMPONENT_GROUP)
#
# This is a catch-all category.  We amp up on the exclusion filter to
# avoid overlap with other categories.
#
ascii_EXCLUDE_FILTER  := $(META_SRC)|dos batch|python|shell|bash|bourne.*again
ascii_INCLUDE_FILTER  := ascii text
ascii_PERMS            = $(DATA_FILE_PERMS)
ascii_OWNER           ?= $(COMPONENT_OWNER)
ascii_GROUP           ?= $(COMPONENT_GROUP)

#============================================================================
# Hide common build macros, idioms, and default rules in a separate file.
#============================================================================
ifeq "$(wildcard zenmagic.mk)" ""
    $(error "Makefile for $(COMPONENT) is unable to include zenmagic.mk.  Please investigate")
else
    include zenmagic.mk
endif

# Specify install-related directories to create as part of the install target.
# NB: Intentional usage of _PREFIX instead of PREFIX here to avoid edge case circular 
# dependency if install directory has same names as install target.

INSTALL_MKDIRS    = $(_DESTDIR)$(_PREFIX)

discovered_src    = $(patsubst %,%.$(DISCOVERED_SRC_EXT),$(BIN_TYPES))
manifest_src      = $(patsubst %,%.$(MANIFEST_SRC_EXT),$(BIN_TYPES))
bintype_mk_files  = $(patsubst %,%.mk,$(BIN_TYPES))
build_dirs        = $(patsubst %,$(BUILD_DIR)/%,$(BIN_TYPES))
abs_build_dirs    = $(patsubst $(BUILD_DIR)/%,$(ABS_BUILD_DIR)/%,$(build_dirs))
install_bintypes := $(patsubst %,install-%,$(BIN_TYPES))

$(INSTALL_MKDIRS) $(ABS_BUILD_DIR) $(abs_build_dirs):
	$(call cmd,MKDIR,$@)


#============================================================================
# Rule to create files like:
#
#     python.mk
#
# from the list of python files specified in:
#
#     python.manifest or python.discovered
#
# depending upon the value of $(USE_MANIFEST_SRC).
#============================================================================
ifeq "$(MAKECMDGOALS)" "install"
$(bintype_mk_files):
	$(error "Please run 'make build' first.")
else
.ONESHELL: $(bintype_mk_files)
.DELETE_ON_ERROR: $(bintype_mk_files)
ifeq "$(USE_MANIFEST_SRC)" "yes"
# e.g., python.mk is dependent upon python.manifest
$(bintype_mk_files): %.mk : %.$(MANIFEST_SRC_EXT)
else
# e.g., python.mk is dependent upon python.discovered
$(bintype_mk_files): ESCAPED_SRC_DIR := $(shell echo $(_SRC_DIR) | sed -e "s|\.|\\\\.|g")
$(bintype_mk_files): %.mk : %.$(DISCOVERED_SRC_EXT)
endif
	@$(call echol,"CREATE $@")
	echo "#$(LINE)" > $@
	echo "# THIS IS A GENERATED FILE.  EDITS TO THIS FILE WILL BE LOST." >> $@
	echo "#" >> $@
	echo "# $* build target : dependencies" >> $@
	echo "#$(LINE)" >> $@
	echo '#BUILD_DIR ?= $(BUILD_DIR)' >> $@
	echo '#ABS_BUILD_DIR ?= $(ABS_BUILD_DIR)' >> $@
	echo '#_SRC_DIR ?= $(_SRC_DIR)' >> $@
	echo '#$*_MAGIC ?= $($*_MAGIC)' >> $@
	echo $*_build = $$(cat $? | sed -e 's|^\($(ESCAPED_SRC_DIR)\)\(.*\)|$$(BUILD_DIR)/$*/\2|g') >> $@
	echo '.PHONY: $*' >> $@
	echo '$* : $$($*_build)' >> $@
	echo >> $@
	echo '.ONESHELL: $$($*_build)' >> $@
	echo '$$($*_build): | $$(ABS_BUILD_DIR)/$*' >> $@
	echo '$$($*_build): NORMALIZE_MAGIC_STRING := -e "1,3s|^\#\!.*|\#!$$($*_MAGIC)|g"' >> $@
	echo '$$($*_build): $$(BUILD_DIR)/$*/% : $$(_SRC_DIR)%' >> $@
	echo "	@if [ -z \"\$$($*_MAGIC)\" ];then" >> $@
	echo '		$$(call cmd_noat,CP,$$<,$$@)' >> $@
	echo "	else" >> $@
	echo '		$$(call cmd_noat,SED,$$(NORMALIZE_MAGIC_STRING),$$<,$$@,#!$$($*_MAGIC))' >> $@
	echo "	fi" >> $@
	echo >> $@
	cat $? | sed -e 's|^\($(ESCAPED_SRC_DIR)\)\(.*\)|$$(BUILD_DIR)/$*/\2 : \1\2|g' >> $@
	echo >> $@
	echo "#$(LINE)" >> $@
	echo "# $* install target : dependencies" >> $@
	echo "# NB: Make the install deps 'existence-only' via the pipe since install should not trigger" >> $@
	echo "#     changes to the build tree." >> $@
	echo "#$(LINE)" >> $@
	echo '#INSTALL_MKDIRS ?= $(INSTALL_MKDIRS)' >> $@
	echo $*_install = $$(cat $? | sed -e 's|^\($(ESCAPED_SRC_DIR)\)\(.*\)|$$(_DESTDIR)$$(_PREFIX)/\2|g') >> $@
	echo '.PHONY: install-$*' >> $@
	echo 'install-$* : $$($*_install)' >> $@
	echo >> $@
	echo '.ONESHELL: $$($*_install)' >> $@
	echo '.PHONY: $$($*_install)' >> $@
	echo '$$($*_install): build_dir = $$(BUILD_DIR)/$*' >> $@
	echo '$$($*_install): bintype   = $*' >> $@
	echo '$$($*_install): INSTALL_PERMS = $($*_PERMS)' >> $@
	echo '$$($*_install): INSTALL_OWNER = $($*_OWNER)' >> $@
	echo '$$($*_install): INSTALL_GROUP = $($*_GROUP)' >> $@
	echo '$$($*_install): | $$(INSTALL_MKDIRS)' >> $@
	echo "	@if [ -f \"\$$(build_dir)/\$$(@F)\" ];then" >> $@
	echo '		$$(call cmd,INSTALL,$$(build_dir)/$$(@F),$$@,$$(INSTALL_PERMS),$$(INSTALL_OWNER),$$(INSTALL_GROUP))' >> $@
	echo "	else" >> $@
	echo '		$$(call echol,"Error: Missing $$(build_dir)/$$(@F).")' >> $@
	echo '		$$(call echol,"Unable to install $$(bintype) files.")' >> $@
	echo '		$$(call echol,"$$(LINE)")' >> $@
	echo '		$$(call echol,"Please run \"make build\" first.")' >> $@
	echo '		exit 1' >> $@
	echo "	fi" >> $@
	echo >> $@
endif


#============================================================================
# Rule to create files like:
#
#    python.discovered  shell.discovered   ..
#
# Walk the _SRC_DIR looking for files of a given type.
# Place the results in a file called <type>.discovered
#
# We're using the primitive:
#
#    /usr/bin/file 
#
# to discern file type rather than rely upon something less definitive 
# like filename alone.
#============================================================================
# NB:  Adding guard-logic to avoid nuisance rebuilds of discovery lists
#      especially during installs when we don't want to affect the build tree.
ifeq "$(filter install install-ascii install-shell install-python install-dosbat install-bash,$(MAKECMDGOALS))" ""
.ONESHELL:        $(discovered_src)
.DELETE_ON_ERROR: $(discovered_src)
$(discovered_src): exclude_filter = $(patsubst %.$(DISCOVERED_SRC_EXT),%_EXCLUDE_FILTER,$@)
$(discovered_src): include_filter = $(patsubst %.$(DISCOVERED_SRC_EXT),%_INCLUDE_FILTER,$@)
$(discovered_src): src_dir        = $(_SRC_DIR)
$(discovered_src): find_opts      = -maxdepth 1 -mindepth 1 -type f -exec file {} \\;
$(discovered_src): filetype       = $(patsubst %.$(DISCOVERED_SRC_EXT),%,$@)
$(discovered_src): | .rediscover
	@if [ -z '$($(include_filter))' ] ;then
		$(call echol,"Error: Detected null value for the $(include_filter) variable.")
		$(call echol,"       Unable to discern which files in $(ABS_SRC_DIR) are $(filetype)-ish files.")
		$(call echol,"       Consider updating the $(COMPONENT) component makefile accordingly.")
		$(call echol,"FAILED $@")
		exit 1
	else
		if [ -z '$($(exclude_filter))' ];then
			if ! (find $(src_dir) $(find_opts) | (egrep -i "$($(include_filter))" | cut -d: -f1 | sort -u > $@); exit $${PIPESTATUS[0]}) ; then
				$(call echol,"Error: find $(src_dir) $(find_opts)")
				$(call echol,"       Unable to discern which files in $(ABS_SRC_DIR) are $(filetype)-ish files.")
				$(call echol,"FAILED $@")
				exit 1
			fi
		else
			if ! (find $(src_dir) $(find_opts) | (egrep -iv "$($(exclude_filter))" | egrep -i "$($(include_filter))" | cut -d: -f1 | sort -u >$@); exit $${PIPESTATUS[0]}) ; then
				$(call echol,"Error: find $(src_dir) $(find_opts)")
				$(call echol,"       Unable to discern which files in $(ABS_SRC_DIR) are $(filetype)-ish files.")
				$(call echol,"FAILED $@")
				exit 1
			fi
		fi
	fi
	if [ -f "$@" -a ! -s "$@" ];then
		$(call echol,"Warning: 0-length $@ file generated.")
		$(call echol,"         This implies that no $(filetype) type files were discovered by my logic in $(ABS_SRC_DIR)")
		$(call echol,"         Consequently files of this type will not be built or installed.")
		format_filetype_and_count=`wc -l $@|cut -d" " -f1|awk '{printf("%-10s [%2s files]\n","$(filetype)",$$1)}'`
		$(call echol,"FOUND  $${format_filetype_and_count} warning")
	else
		format_filetype_and_count=`wc -l $@|cut -d" " -f1|awk '{printf("%-10s [%2s files]\n","$(filetype)",$$1)}'|sed -e "s| 1 files| 1 file |g"`
		$(call echol,"FOUND  $${format_filetype_and_count}")
	fi
endif

#============================================================================
# Trigger the discovery of various 'binary' files in the source tree via:
#
#    make discover
#
# This generally amounts to python and shell scripts of various flavors.
#
# The overall work-flow is:
#
# 1. Add or delete 'binary' files in the src directory.
# 2. Run 'make clean discover build install'
# 3. If you're happy with the result:
#        'make manifests'
# 4. Check-in the generated/updated *.manifest files.
# 5. Production build will use your checked in manifest with the next build.
#============================================================================
.PHONY: discover
.ONESHELL: discover
discover:
	@$(foreach target_file,$(wildcard $(discovered_src) $(bintype_mk_files) .rediscover),$(call cmd_noat,RM,$(target_file));)
	$(MAKE)  -s --no-print-directory  $(discovered_src)
	$(MAKE)  -s --no-print-directory  $(bintype_mk_files)

.rediscover:
	$(call cmd,TOUCH,$@)

.PHONY: manifests
manifests: $(manifest_src)

ifeq "$(filter manifests install install-ascii install-shell install-python install-dosbat install-bash,$(MAKECMDGOALS))" ""
    ifeq "$(USE_MANIFEST_SRC)" "yes"
$(manifest_src): | $(patsubst %.$(MANIFEST_SRC_EXT),%.$(DISCOVERED_SRC_EXT),$@)
	$(call cmd,CP,$?,$@)
    else
$(manifest_src): %.$(MANIFEST_SRC_EXT) : %.$(DISCOVERED_SRC_EXT)
	$(call cmd,CP,$?,$@)
    endif
else
$(manifest_src): %.$(MANIFEST_SRC_EXT) : %.$(DISCOVERED_SRC_EXT)
	$(call cmd,CP,$?,$@)
endif

help: dflt_component_help

no-include-targets  = devinstall help discover manifests $(manifest_src) $(discovered_src) distclean mrclean clean uninstall clean-mk dflt_component_clean dflt_component_help dflt_component_uninstall $(INSTALL_MKDIRS) $(ABS_BUILD_DIR) $(abs_build_dirs) checkenv
ifeq "$(filter $(no-include-targets),$(MAKECMDGOALS))" ""
    ifneq "$(MAKECMDGOALS)" ""
        #$(warning "including *.mk makefiles")
        -include ascii.mk
        -include bash.mk
        -include dosbat.mk
        -include python.mk
        -include shell.mk
    endif
endif

clean:
	@if [ -d "$(BUILD_TOP)" ];then \
		if [ "$(ABS_BUILD_DIR)" != "$(ABS_SRC_DIR)" ];then \
			$(call cmd_noat,RMDIR,$(BUILD_TOP)) ;\
		else \
			$(call echol,"Error: Ignorning request to remove the build directory which is") ;\
			$(call echol,"       currently the same as your source directory.") ;\
			$(call echol,$(LINE)) ;\
			$(call echol,"       ABS_BUILD_DIR $(ABS_BUILD_DIR)") ;\
			$(call echol,"       ABS_SRC_DIR   $(ABS_SRC_DIR)") ;\
		fi ;\
	fi
	@$(foreach target_file,$(wildcard $(discovered_src) $(bintype_mk_files) .rediscover),$(call cmd_noat,RM,$(target_file));)

mrclean distclean: clean dflt_component_distclean
	@if [ -d "$(_DESTDIR)$(_PREFIX)" ];then \
		count=$(shell ls -a1 $(_DESTDIR)$(_PREFIX) 2>/dev/null|wc -l) ;\
		if ((count >= 3 ));then \
			echo "You may also run 'make uninstall' to uninstall from $(_DESTDIR)$(_PREFIX)" ;\
		fi ;\
	fi

build: checkenv $(BIN_TYPES)

.PHONY: install
ifeq "$(wildcard $(bintype_mk_files))" ""
install:
	@$(call echol,"Please run 'make build' first.")
else
install: $(install_bintypes)
endif

.PHONY : devinstall
devinstall: dflt_devinstall

uninstall: dflt_component_uninstall
