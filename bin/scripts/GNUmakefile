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
MAKEFLAGS     += -r

SHELL := $(shell which bash)

#============================================================================
# Build component configuration.
#
# Beware of trailing spaces.
# Don't let your editor turn tabs into spaces or vice versa.
#============================================================================
COMPONENT              = scripts
SCRIPT_TYPES           = ascii bash python # shell dosbat
USE_MANIFEST_SRC      ?= no
USE_DELTA_INSTALL     ?= yes
# Specify where the source files live.
srcdir                 = .
# Specify the install directory (e.g., /opt/zenoss/bin).  See zenmagic.mk.
instdir                = $(bindir)
bldtop                 = build

# Normalize src dir by adding trailing slash.
_srcdir               := $(shell echo $(strip $(srcdir)) | sed -e "s|\([^\/]\)$$|\1\/|g")
ifeq "$(USE_MANIFEST_SRC)" "yes"
blddir                 = $(bldtop)/$(COMPONENT).manifest
else
blddir                 = $(bldtop)/$(COMPONENT).discovered
endif

ABS_blddir            := $(abspath $(blddir))
ABS_srcdir            := $(abspath $(_srcdir))
DISCOVERED_SRC_EXT    := discovered
MANIFEST_SRC_EXT      := manifest
metasrc               = GNUmakefile|zenmagic\.mk|.*\.mk|$(COMPONENT)\.log|\.git.*|\.svn.*|.*\.$(DISCOVERED_SRC_EXT)|\.checked.*|.*\.$(MANIFEST_SRC_EXT)|.*\.log
#
bash_EXCLUDE_FILTER   := $(metasrc)
bash_INCLUDE_FILTER   := bash|bourne.*again
bash_MAGIC            := /bin/bash
bash_PERMS             = $(EXEC_FILE_PERMS)
bash_OWNER            ?= $(INST_OWNER)
bash_GROUP            ?= $(INST_GROUP)
#
dosbat_EXCLUDE_FILTER := $(metasrc)
dosbat_INCLUDE_FILTER := dos batch
dosbat_PERMS           = $(EXEC_FILE_PERMS)
dosbat_OWNER          ?= $(INST_OWNER)
dosbat_GROUP          ?= $(INST_GROUP)
#
python_EXCLUDE_FILTER := $(metasrc)
python_INCLUDE_FILTER := python
python_MAGIC          := /usr/bin/env python
python_PERMS           = $(EXEC_FILE_PERMS)
python_OWNER          ?= $(INST_OWNER)
python_GROUP          ?= $(INST_GROUP)
#
shell_EXCLUDE_FILTER  := $(metasrc)|bash|bourne.*again
shell_INCLUDE_FILTER  := shell script
shell_MAGIC           := /bin/sh
shell_PERMS            = $(EXEC_FILE_PERMS)
shell_OWNER           ?= $(INST_OWNER)
shell_GROUP           ?= $(INST_GROUP)
#
# This is a catch-all category.  We amp up on the exclusion filter to
# avoid overlap with other categories.
#
ascii_EXCLUDE_FILTER  := $(metasrc)|dos batch|python|shell|bash|bourne.*again
ascii_INCLUDE_FILTER  := ascii text
ascii_PERMS            = $(DATA_FILE_PERMS)
ascii_OWNER           ?= $(INST_OWNER)
ascii_GROUP           ?= $(INST_GROUP)

#============================================================================
# Hide common build macros, idioms, and default rules in a separate file.
#============================================================================

#---------------------------------------------------------------------------#
# Pull in zenmagic.mk
#---------------------------------------------------------------------------#
# Locate and include common build idioms tucked away in 'zenmagic.mk'
# This holds convenience macros and default target implementations.
#
# Generate a list of directories starting here and going up the tree where we
# should look for an instance of zenmagic.mk to include.
#
#     ./zenmagic.mk ../zenmagic.mk ../../zenmagic.mk ../../../zenmagic.mk
#---------------------------------------------------------------------------#
NEAREST_ZENMAGIC_MK := $(word 1,$(wildcard ./zenmagic.mk $(shell for slash in $$(echo $(abspath .) | sed -e "s|.*\(/obj/\)\(.*\)|\1\2|g" -e "s|.*\(/src/\)\(.*\)|\1\2|g" | sed -e "s|[^/]||g" -e "s|/|/ |g"); do string=$${string}../;echo $${string}zenmagic.mk; done | xargs echo)))

ifeq "$(NEAREST_ZENMAGIC_MK)" ""
    $(warning "Missing zenmagic.mk needed by the $(COMPONENT)-component makefile.")
    $(warning "Unable to find our file of build idioms in the current or parent directories.")
    $(error   "A fully populated src tree usually resolves that.")
else
    #ifneq "$(MAKECMDGOALS)" ""
    #    $(warning "Including $(NEAREST_ZENMAGIC_MK) $(MAKECMDGOALS)")
    #endif
    include $(NEAREST_ZENMAGIC_MK)
endif

# Specify install-related directories to create as part of the install target.

discovered_src    = $(patsubst %,$(blddir)/%.$(DISCOVERED_SRC_EXT),$(SCRIPT_TYPES))
manifest_src      = $(patsubst %,%.$(MANIFEST_SRC_EXT),$(SCRIPT_TYPES))
script_mk_files   = $(patsubst %,$(blddir)/%.mk,$(SCRIPT_TYPES))
build_dirs        = $(patsubst %,$(blddir)/%,$(SCRIPT_TYPES))
abs_build_dirs    = $(patsubst $(blddir)/%,$(ABS_blddir)/%,$(build_dirs))
install_scripts  := $(patsubst %,install-%,$(SCRIPT_TYPES))

BUILD_MKDIRS := $(shell echo $(blddir) $(ABS_blddir) $(abs_build_dirs) | sort -u)

$(BUILD_MKDIRS):
	$(call cmd,MKDIR,$@)

INSTALL_MKDIRS = $(_DESTDIR)$(bindir)
$(INSTALL_MKDIRS):
	@($(call cmd_noat,MKDIR,$@)) ;\
	rc=$$? ;\
	if [ $${rc} -ne 0 ] ; then \
		echo $(LINE) ;\
		echo "Maybe you intended 'sudo make install' or 'make installhere' instead?" ;\
		echo ;\
		exit $${rc} ;\
	else \
		$(call cmd_noat,CHOWN,$(INST_OWNER),$(INST_GROUP),$@) ;\
		rc=$$? ;\
		if [ $${rc} -ne 0 ] ; then \
			exit $${rc} ;\
		fi ;\
	fi

#============================================================================
# Rule to create files like:
#
#     python.mk bash.mk ..
#
# from the list of files respectiviely specified in:
#
#     python.manifest or python.discovered
#     bash.manifest   or bash.discovered
#     ..
#
# depending upon the value of $(USE_MANIFEST_SRC).
#
# These makefiles implement a glorified copy from 
#
#     srcdir to blddir to install dir
#
# with the added ability to normalize magic strings, file ownership, 
# and file permissions as desired.
#============================================================================
install-targets = install
ifneq "$(filter $(install-targets),$(MAKECMDGOALS))" ""
$(script_mk_files):
	$(error "Please run 'make build' first.")
else
.DELETE_ON_ERROR: $(script_mk_files)
$(script_mk_files): ESCAPED_srcdir := $(shell echo $(_srcdir) | sed -e "s|\.|\\\\.|g")
$(script_mk_files): | $(blddir)
ifeq "$(USE_MANIFEST_SRC)" "yes"
# e.g., python.mk is dependent upon python.manifest
$(script_mk_files): $(blddir)/%.mk : %.$(MANIFEST_SRC_EXT)
else
# e.g., python.mk is dependent upon python.discovered
$(script_mk_files): %.mk : %.$(DISCOVERED_SRC_EXT)
endif
	@$(call echol,"create $@","CREATE $@")
	@echo "#$(LINE)" > $@; \
	echo "# THIS IS A GENERATED FILE.  EDITS TO THIS FILE WILL BE LOST." >> $@; \
	echo "#" >> $@; \
	echo "# $(*F) build target : dependencies" >> $@; \
	echo "#$(LINE)" >> $@; \
	echo '# blddir      = $(blddir)' >> $@; \
	echo '# ABS_blddir  = $(ABS_blddir)' >> $@; \
	echo '# _srcdir     = $(_srcdir)' >> $@; \
	echo '# $(*F)_MAGIC = $($(*F)_MAGIC)' >> $@; \
	echo '# cmd_uses_stdio = $(cmd_uses_stdio)' >> $@; \
	echo "#$(LINE)" >> $@; \
	echo $(*F)_build = $$(cat $? | sed -e 's|^\($(ESCAPED_srcdir)\)\(.*\)|$$(blddir)/$(*F)/\2|g') >> $@; \
	echo '.PHONY: $(*F)' >> $@; \
	echo '$(*F) : $$($(*F)_build)' >> $@; \
	echo >> $@; \
	echo '$$($(*F)_build): | $$(ABS_blddir)/$(*F)' >> $@; \
	echo '$$($(*F)_build): NORMALIZE_MAGIC_STRING := -e "1,3s|^\#\!.*|\#!$$($(*F)_MAGIC)|g"' >> $@; \
	echo '$$($(*F)_build): ESC_NORMALIZE_MAGIC_STRING := -e \"1,3s|^\#\!.*|\#!$$($(*F)_MAGIC)|g\"' >> $@; \
	echo '$$($(*F)_build): $$(blddir)/$(*F)/% : $$(_srcdir)%' >> $@; \
	echo "	@if [ -z \"\$$($(*F)_MAGIC)\" ];then \\" >> $@; \
	echo '		$$(call cmd_noat,CP,$$<,$$@); \' >> $@; \
	echo '		rc=$$$$?; \' >> $@; \
	echo '		if [ $$$${rc} -ne 0 ];then \' >> $@; \
	echo '			exit $$$${rc}; \' >> $@; \
	echo '		fi \' >> $@; \
	echo "	else \\" >> $@; \
	echo '		$(call echobothl,"$$(SED) $$(ESC_NORMALIZE_MAGIC_STRING) $$< > $$@","SED    #!$$($(*F)_MAGIC) $$<"); \' >> $@; \
	echo '		$(SED) $$(NORMALIZE_MAGIC_STRING) $$< > $$@; \' >> $@; \
	echo '		rc=$$$$?; \' >> $@; \
	echo '		if [ $$$${rc} -ne 0 ];then \' >> $@; \
	echo '			exit $$$${rc}; \' >> $@; \
	echo '		fi \' >> $@; \
	echo "	fi" >> $@; \
	echo >> $@; \
	cat $? | sed -e 's|^\($(ESCAPED_srcdir)\)\(.*\)|$$(blddir)/$(*F)/\2 : \1\2|g' >> $@; \
	echo >> $@; \
	echo "#$(LINE)" >> $@; \
	echo "# $* install target : dependencies" >> $@; \
	echo "# NB: Make the install deps 'existence-only' via the pipe since install should not trigger" >> $@; \
	echo "#     changes to the build tree." >> $@; \
	echo "#$(LINE)" >> $@; \
	echo '# bindir            = $(bindir)' >> $@; \
	echo '# _DESTDIR          = $(_DESTDIR)' >> $@; \
	echo '# INSTALL_MKDIRS    = $(INSTALL_MKDIRS)' >> $@; \
	echo '# USE_DELTA_INSTALL = $(USE_DELTA_INSTALL)' >> $@; \
	echo "#$(LINE)" >> $@; \
	echo $(*F)_install = $$(cat $? | sed -e 's|^\($(ESCAPED_srcdir)\)\(.*\)|$$(_DESTDIR)$$(bindir)/\2|g') >> $@; \
	echo '.PHONY: install-$(*F)' >> $@; \
	echo 'install-$(*F) : $$($(*F)_install)' >> $@; \
	echo >> $@; \
	echo 'ifeq "$$(USE_DELTA_INSTALL)" "yes"' >> $@; \
	echo '#.PHONY: $$($(*F)_install)' >> $@; \
	echo 'else' >> $@; \
	echo '.PHONY: $$($(*F)_install)' >> $@; \
	echo 'endif' >> $@; \
	echo '$$($(*F)_install): build_dir = $$(blddir)/$(*F)' >> $@; \
	echo '$$($(*F)_install): scripttype    = $(*F)' >> $@; \
	echo '$$($(*F)_install): INSTALL_PERMS = $($(*F)_PERMS)' >> $@; \
	echo '$$($(*F)_install): INSTALL_OWNER = $($(*F)_OWNER)' >> $@; \
	echo '$$($(*F)_install): INSTALL_GROUP = $($(*F)_GROUP)' >> $@; \
	echo '$$($(*F)_install): | $$(INSTALL_MKDIRS)' >> $@; \
	echo 'ifeq "$$(USE_DELTA_INSTALL)" "yes"' >> $@; \
	echo '$$($(*F)_install): $$(_DESTDIR)$$(bindir)/% : $$(blddir)/$(*F)/%' >> $@; \
	echo 'endif' >> $@; \
	echo "	@if [ -f \"\$$(build_dir)/\$$(@F)\" ];then \\" >> $@; \
	echo '		$$(call cmd_noat,INSTALL,$$(build_dir)/$$(@F),$$@,$$(INSTALL_PERMS),$$(INSTALL_OWNER),$$(INSTALL_GROUP)); \' >> $@; \
	echo '		rc=$$$$?; \' >> $@; \
	echo '		if [ $$$${rc} -ne 0 ];then \' >> $@; \
	echo '			exit $$$${rc}; \' >> $@; \
	echo '		fi \' >> $@; \
	echo "	else \\" >> $@; \
	echo '		$$(call echol,"Error: Missing $$(build_dir)/$$(@F)."); \' >> $@; \
	echo '		$$(call echol,"Unable to install $$(scripttype) files."); \' >> $@; \
	echo '		$$(call echol,"$$(LINE)"); \' >> $@; \
	echo '		$$(call echol,"Please run \"make build\" first."); \' >> $@; \
	echo '		exit 1; \' >> $@; \
	echo "	fi" >> $@; \
	echo >> $@; \
	echo 'ifeq "$$(USE_DELTA_INSTALL)" "yes"' >> $@; \
	cat $? | sed -e 's|^\($(ESCAPED_srcdir)\)\(.*\)|$$(_DESTDIR)$$(bindir)/\2 : $$(blddir)/$(*F)/\2|g' >> $@; \
	echo 'endif' >> $@
endif


#============================================================================
# Rule to create files like:
#
#    python.discovered  shell.discovered   ..
#
# Walk the _srcdir looking for files of a given type.
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

#      Also, depend upon a checked environment so we ensure uplevel version of make
#      that won't fail on the .ONESHELL idiom used here.

ifeq "$(filter install install-ascii install-shell install-python install-dosbat install-bash,$(MAKECMDGOALS))" ""
.DELETE_ON_ERROR: $(discovered_src)
$(discovered_src): exclude_filter = $(patsubst $(blddir)/%.$(DISCOVERED_SRC_EXT),%_EXCLUDE_FILTER,$@)
$(discovered_src): include_filter = $(patsubst $(blddir)/%.$(DISCOVERED_SRC_EXT),%_INCLUDE_FILTER,$@)
$(discovered_src): src_dir        = $(_srcdir)
$(discovered_src): find_opts      = -maxdepth 1 -mindepth 1 -type f -exec file {} \\;
$(discovered_src): filetype       = $(patsubst $(blddir)/%.$(DISCOVERED_SRC_EXT),%,$@)
$(discovered_src): | .rediscover $(CHECKED_ENV) $(blddir)
	@if [ -z '$($(include_filter))' ] ;then \
		$(call echol,"Error: Detected null value for the $(include_filter) variable."); \
		$(call echol,"       Unable to discern which files in $(ABS_srcdir) are $(filetype)-ish files."); \
		$(call echol,"       Consider updating the $(COMPONENT) component makefile accordingly."); \
		$(call echol,"FAILED $@"); \
		exit 1; \
	else \
		if [ -z '$($(exclude_filter))' ];then \
			if ! (find $(src_dir) $(find_opts) | (egrep -i "$($(include_filter))" | cut -d: -f1 | sort -u > $@); exit $${PIPESTATUS[0]}) ; then \
				$(call echol,"Error: find $(src_dir) $(find_opts)"); \
				$(call echol,"       Unable to discern which files in $(ABS_srcdir) are $(filetype)-ish files."); \
				$(call echol,"FAILED $@"); \
				exit 1; \
			fi; \
		else \
			if ! (find $(src_dir) $(find_opts) | (egrep -iv "$($(exclude_filter))" | egrep -i "$($(include_filter))" | cut -d: -f1 | sort -u >$@); exit $${PIPESTATUS[0]}) ; then \
				$(call echol,"Error: find $(src_dir) $(find_opts)"); \
				$(call echol,"       Unable to discern which files in $(ABS_srcdir) are $(filetype)-ish files."); \
				$(call echol,"FAILED $@"); \
				exit 1; \
			fi; \
		fi; \
	fi; \
	if [ -f "$@" -a ! -s "$@" ];then \
		$(call echol,"Warning: 0-length $@ file generated."); \
		$(call echol,"         This implies that no $(filetype) type files were discovered by my logic in:"); \
		$(call echol,"            $(ABS_srcdir)"); \
		$(call echol,"         Consequently files of this type will not be built or installed."); \
		format_filetype_and_count=`wc -l $@|cut -d" " -f1|awk '{printf("%-10s [%2s files]\n","$(filetype)",$$1)}'`; \
		$(call echol,"found $${format_filetype_and_count} warning","FOUND  $${format_filetype_and_count} warning"); \
	else \
		format_filetype_and_count=`wc -l $@|cut -d" " -f1|awk '{printf("%-10s [%2s files]\n","$(filetype)",$$1)}'|sed -e "s| 1 files| 1 file |g"`; \
		$(call echol,"found $${format_filetype_and_count}","FOUND  $${format_filetype_and_count}"); \
	fi
endif

#============================================================================
# Trigger the discovery of various 'binary' script files in the source tree via:
#
#    make discover
#
# This generally amounts to python and shell scripts of various flavors.
#
# The overall work-flow is:
#
# 1. Add or delete 'binary' script files in the src directory.
# 2. Run 'make clean discover build install'
# 3. If you're happy with the result:
#        'make manifests'
# 4. Check-in the generated/updated *.manifest files.
# 5. Production build will use your checked in manifest with the next build.
#============================================================================
.PHONY: discover
#.ONESHELL: discover
discover:
	@$(foreach target_file,$(wildcard $(discovered_src) $(script_mk_files) .rediscover),$(call cmd_noat,RM,$(target_file));)
	$(MAKE)  -s --no-print-directory  $(discovered_src)
	$(MAKE)  -s --no-print-directory  $(script_mk_files)

.rediscover:
	$(call cmd,TOUCH,$@)

.PHONY: manifests
manifests: $(manifest_src)

$(manifest_src): | $(CHECKED_ENV)
ifeq "$(filter manifests install install-ascii install-shell install-python install-dosbat install-bash,$(MAKECMDGOALS))" ""
    ifeq "$(USE_MANIFEST_SRC)" "yes"
$(manifest_src): | $(patsubst %.$(MANIFEST_SRC_EXT),$(blddir)/%.$(DISCOVERED_SRC_EXT),$@)
    else
$(manifest_src): %.$(MANIFEST_SRC_EXT) : $(blddir)/%.$(DISCOVERED_SRC_EXT)
    endif
else
$(manifest_src): %.$(MANIFEST_SRC_EXT) : $(blddir)/%.$(DISCOVERED_SRC_EXT)
endif
	@if [ -f "$<" ];then \
		$(call cmd_noat,CP_interactive,$<,$@) ;\
	else \
		$(call echol,"Unable to create $@ from (missing) $(patsubst %.$(MANIFEST_SRC_EXT),$(blddir)/%.$(DISCOVERED_SRC_EXT),$@)") ;\
	fi

help: dflt_component_help
	@echo Using common build idioms from $(NEAREST_ZENMAGIC_MK)
	@echo

no-include-targets  = devinstall help discover manifests $(manifest_src) $(discovered_src) distclean mrclean clean uninstall uninstallhere clean-mk dflt_component_clean dflt_component_help dflt_component_uninstall $(INSTALL_MKDIRS) $(ABS_blddir) $(abs_build_dirs) checkenv
ifeq "$(filter $(no-include-targets),$(MAKECMDGOALS))" ""
    ifneq "$(MAKECMDGOALS)" ""
        #$(warning "including *.mk makefiles")
        -include $(blddir)/ascii.mk
        -include $(blddir)/bash.mk
        -include $(blddir)/dosbat.mk
        -include $(blddir)/python.mk
        -include $(blddir)/shell.mk
    endif
endif

clean:
	@for target_file in $(wildcard $(discovered_src) $(script_mk_files) .rediscover) ;\
	do \
		$(call echol,"rm -f $${target_file}","RM     $${target_file}") ;\
		rm -rf "$${target_file}" ;\
		rc=$$? ;\
		if [ $${rc} -ne 0 ];then \
			exit $${rc} ;\
		fi ;\
	done
	@if [ -d "$(bldtop)" ];then \
		if [ "$(ABS_blddir)" != "$(ABS_srcdir)" ];then \
			$(call cmd_noat,RMDIR,$(bldtop)) ;\
		else \
			$(call echol,"Error: Ignorning request to remove the build directory which is") ;\
			$(call echol,"       currently the same as your source directory.") ;\
			$(call echol,$(LINE)) ;\
			$(call echol,"       ABS_blddir $(ABS_blddir)") ;\
			$(call echol,"       ABS_srcdir   $(ABS_srcdir)") ;\
		fi ;\
	fi

mrclean distclean: clean dflt_component_distclean
	@if [ -d "$(_DESTDIR)$(bindir)" ];then \
		count=$(shell ls -a1 $(_DESTDIR)$(bindir) 2>/dev/null|wc -l) ;\
		if ((count >= 3 ));then \
			echo "You may also run 'make uninstall' to uninstall from $(_DESTDIR)$(bindir)" ;\
		fi ;\
	fi
	@if [ -d "$(heredir)$(bindir)" ];then \
		count=$(shell ls -a1 $(heredir)$(bindir) 2>/dev/null|wc -l) ;\
		if ((count >= 3 ));then \
			echo "You may also run 'make uninstallhere' to uninstall from $(heredir)$(bindir)" ;\
		fi ;\
	fi
	@if [ -f "$(COMPONENT).log" ];then \
		rm $(COMPONENT).log ;\
	fi

build: $(CHECKED_ENV) $(SCRIPT_TYPES)

.PHONY: install installhere
ifeq "$(wildcard $(script_mk_files))" ""
install:
	@$(call echol,"Please run 'make build' first.")
else
install : $(install_scripts)
endif
installhere : $(install_scripts)

.PHONY: devinstall
devinstall: dflt_devinstall

.PHONY: uninstall
uninstall: dflt_component_uninstall
	@if [ -d "$(_DESTDIR)$(bindir)" ];then \
		count=`ls -a1 $(_DESTDIR)$(bindir) 2>/dev/null|wc -l` ;\
		if ((count < 3 ));then \
			($(call cmd_noat,RMDIR,$(_DESTDIR)$(bindir))) ;\
			rc=$$? ;\
			if [ $${rc} -ne 0 ] ; then \
				echo $(LINE) ;\
				echo "Maybe you intended 'sudo make $@' instead?" ;\
				echo ;\
				exit $${rc} ;\
			fi ;\
		fi ;\
	fi

.PHONY: uninstallhere
uninstallhere: uninstall
	@if [ -d "$(heredir)" ];then \
		$(call cmd_noat,RMDIR,$(heredir)) ;\
	fi
