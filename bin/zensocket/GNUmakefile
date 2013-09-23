#============================================================================
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
#============================================================================
.DEFAULT_GOAL := build # build|help

PROGRAM        = zensocket

# Define install-related attributes.

PROGRAM_PERMS  = 04750
PROGRAM_OWNER  = root
ZENHOME       ?= /opt/zenoss
PREFIX        ?= $(ZENHOME)/bin
INSTDIR        = $(DESTDIR)$(PREFIX)

# Define build-related attributes

BUILD_DIR           = obj
INCLUDE_SYSINC_DEPS = no
INCLUDE_DEBUG_SYMS  = yes
REQUIRES_GCC        = 1

#============================================================================
# Compiling and Linking Configuration
#============================================================================
ifeq "$(INCLUDE_DEBUG_SYMS)" "yes"
    GCC_DEBUG_OPTS = -g
else
    GCC_DEBUG_OPTS =
endif

CFLAGS   = $(GCC_DEBUG_OPTS)
CFLAGS  += -Wall -pedantic 
#CFLAGS += -Wno-unused-but-set-variable
CPPFLAGS = -D__GNU_LIBRARY__


#============================================================================
# Convenience Macros
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
#
# Stop at the closest instance.  Also, stop if we hit a directory called 
# 'obj' or 'src' since we're probably outside the sandbox otherwise.
#---------------------------------------------------------------------------#
NEAREST_ZENMAGIC_MK := $(word 1,$(wildcard ./zenmagic.mk $(shell for slash in $$(echo $(abspath .) | sed -e "s|.*\(/obj/\)\(.*\)|\1\2|g" -e "s|.*\(/src/\)\(.*\)|\1\2|g" | egrep "^/obj|^/src" | sed -e "s|[^/]||g" -e "s|/|/ |g"); do string=$${string}../;echo $${string}zenmagic.mk; done | xargs echo)))

ifeq "$(NEAREST_ZENMAGIC_MK)" ""
    $(warning "Missing zenmagic.mk")
    $(warning "Unable to find our file of build idioms in the current or parent directories.")
    $(error   "A fully populated src tree usually resolves that.")
else
    #ifneq "$(MAKECMDGOALS)" ""
    #    $(warning "Including $(NEAREST_ZENMAGIC_MK) $(MAKECMDGOALS)")
    #endif
    include $(NEAREST_ZENMAGIC_MK)
endif

# Primitive to use when installing files.
INSTALL  = install
LINE     = "-----------------------------------------------------------------------------"

#---------------------------------------------------------------------------#
# Configure gcc to dump out header files actually used at compile-time.
#---------------------------------------------------------------------------#

GCC_MAKE_DEPENDENCY_RULES = -M
ifeq "$(INCLUDE_SYSINC_DEPS)" "yes"
    SUPPRESS_SYSINC_DEPS =
else
    # Do not include system header directories (nor headers files that are
    # included directly or indirectly from such headers).  These hardly
    # ever change so making rebuilds sensitive to their modtimes is
    # usually overkill.
    SUPPRESS_SYSINC_DEPS = M
endif

# Give us control on the name of the dependency file (e.g., hello.d).
GCC_MAKE_DEP_FILENAME = -MF

# Work-around errors make gives if you remove header files without 
# updating the makefile to match.
GCC_MAKE_PHONY_TARGETS = -MP

# Override target of emitted dependency rule so we can include proper
# pathing to our objdir.
GCC_MAKE_MOD_TARGET_PATH  = -MT
GCC ?= gcc
# $(call make-depend,source-file,object-file,depend-file)
define make-depend 
    $(GCC) $(CFLAGS) $(CPPFLAGS) $(TARGET_ARCH) $1\
	$(GCC_MAKE_DEPENDENCY_RULES)$(SUPPRESS_SYSINC_DEPS)\
	$(GCC_MAKE_PHONY_TARGETS)    \
	$(GCC_MAKE_MOD_TARGET_PATH) $2  \
	$(GCC_MAKE_DEP_FILENAME) $3 
endef


#============================================================================
# Build Targets
#============================================================================
ifneq "$(MAKECMDGOALS)" "clean"
    -include $(BUILD_DIR)/$(PROGRAM).d
endif

.PHONY: all build $(PROGRAM)
all build $(PROGRAM): $(BUILD_DIR)/$(PROGRAM)

$(BUILD_DIR):
	mkdir -p $@

$(INSTDIR):
	@echo mkdir -p $@
	@if ! mkdir -p $@ ;then \
		echo "[$@] Maybe you intended 'sudo make install' instead?" ;\
		exit 1 ;\
	fi

$(BUILD_DIR)/$(PROGRAM): $(BUILD_DIR)/$(PROGRAM).o
	$(LINK.c) $^ $(LOADLIBES) $(LDLIBS) -o $@

$(BUILD_DIR)/$(PROGRAM).o: | $(CHECKED_ENV)
$(BUILD_DIR)/$(PROGRAM).o: | $(PYTHON_INCDIR)
$(BUILD_DIR)/$(PROGRAM).o: | $(BUILD_DIR)
$(BUILD_DIR)/$(PROGRAM).o: $(PROGRAM).c
	$(call make-depend,$<,$@,$(subst .o,.d,$@))
	$(COMPILE.c) $(OUTPUT_OPTION) $<

BUILT_FILES = $(wildcard $(patsubst %,$(BUILD_DIR)/%,$(PROGRAM) $(PROGRAM).o $(PROGRAM).d))
.PHONY: clean
clean:
	@for builtfile in $(BUILT_FILES);\
	do \
		echo "rm $${builtfile}" ;\
		rm $${builtfile} ;\
	done
	@if [ -d "$(BUILD_DIR)" ];then \
		count=`ls -a1 $(BUILD_DIR) 2>/dev/null|wc -l` ;\
		if ((count < 3 ));then \
			echo "rm -rf $(BUILD_DIR)" ;\
			rm -rf $(BUILD_DIR) ;\
		fi ;\
	fi

.PHONY: mrclean distclean
mrclean distclean: clean dflt_component_distclean
	@if [ -e "$(INSTDIR)/$(PROGRAM)" ];then \
		count=$(shell ls -a1 $(INSTDIR) 2>/dev/null|wc -l) ;\
		if ((count >= 3 ));then \
			echo "You may also run 'make uninstall' to uninstall $(PROGRAM) from $(INSTDIR)" ;\
		fi ;\
	fi

.PHONY: install
install: | $(INSTDIR)
install:
	@if [ ! -f "$(BUILD_DIR)/$(PROGRAM)" ]; then \
		echo "Unable to install $(PROGRAM).  Missing $(BUILD_DIR)/$(PROGRAM)." ;\
		echo $(LINE) ;\
		echo "Run 'make build' first" ;\
		echo ;\
		exit 1 ;\
	fi
	@if [ -z "$(INSTDIR)" ]; then \
		echo "[$@] Error: The INSTDIR variable must be set to something before I can install $(PROGRAM) there." ;\
		exit 1 ;\
	fi
	@echo "$(INSTALL) -m $(PROGRAM_PERMS) -o $(PROGRAM_OWNER) $(BUILD_DIR)/$(PROGRAM) $(INSTDIR)"
	@if ! $(INSTALL) -m $(PROGRAM_PERMS) -o $(PROGRAM_OWNER) $(BUILD_DIR)/$(PROGRAM) $(INSTDIR) ;then \
		echo $(LINE) ;\
		install_woe=`$(INSTALL) -m $(PROGRAM_PERMS) -o $(PROGRAM_OWNER) $(BUILD_DIR)/$(PROGRAM) $(INSTDIR) 2>&1` ;\
		case $${install_woe} in \
			*cannot*overwrite*directory*) \
				echo "[$@] Error: Whoa. You seem to have a directory where a file was expected?" ;\
				echo "                 Something went wrong or this is a hybrid dev environment." ;\
				echo "                 Abandoning install attempt." ;\
				ls -ld $(INSTDIR)/$(PROGRAM) ;\
				:;;\
			*cannot*change*ownership*) \
				echo "[$@] Error: Here is what you attempted to overwrite:" ;\
				ls -ld $(INSTDIR)/$(PROGRAM) ;\
				echo "                 Maybe you intended 'sudo make install' instead?" ;\
				:;;\
			*Permission*denied*) \
				echo "[$@] Error: Here is where you attempted to install:" ;\
				ls -ld $(INSTDIR) ;\
				echo "                 Maybe you intended 'sudo make install' instead?" ;\
				:;;\
			*) \
				echo "Please investigate." ;\
				:;;\
		esac ;\
		echo ;\
		exit 1 ;\
	fi

INSTFILES = $(wildcard $(patsubst %,$(INSTDIR)/%,$(PROGRAM) $(PROGRAM).dSYM))
.PHONY: uninstall
uninstall:
	@for instfile in $(INSTFILES);\
	do \
		echo "rm $${instfile}" ;\
		rm $${instfile} ;\
	done
	@count=`ls -a1 $(INSTDIR) 2>/dev/null|wc -l` ;\
	if ((count < 3 ));then \
		echo "rm -rf $(INSTDIR)" ;\
		rm -rf $(INSTDIR) ;\
	fi

.PHONY: help
help: dflt_component_help
	@echo Using common build idioms from $(NEAREST_ZENMAGIC_MK)
	@echo
