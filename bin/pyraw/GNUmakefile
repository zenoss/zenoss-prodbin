#============================================================================
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
#============================================================================
.DEFAULT_GOAL := help # build|help

PROGRAM = pyraw

# Define install-related attributes.

PROGRAM_PERMS    = 04750
PROGRAM_OWNER    = root
ZENHOME         ?= /opt/zenoss
PREFIX          ?= $(ZENHOME)/bin
INSTDIR          = $(DESTDIR)$(PREFIX)

# Define build-related attributes

BUILD_DIR                = obj
WITH_ZENOSS_PYTHON_DEVEL = yes
INCLUDE_SYSINC_DEPS      = no
PYTHON_MAJ_MIN_VER       = 2.7
REQUIRES_GCC             = 1
IGNORE_LD_LIBRARY_PATH   = yes
# Dump out a PROGRAM's link-time dependencies to $(BUILD_DIR)/PROGRAM.dlibs
# This does not materially affect the build, but it does provide a means
# for understanding where certain library dependencies are creeping in.
DUMP_LD_LIBDEPS          = yes

#============================================================================
# Compiling and Linking Configuration
#============================================================================
# Locate python headers and libs to build against.

# At build time, we're locating:
#
#     Python.h         via PYTHON_INCDIR
#     libpythonX.Y.so  via PYTHON_LIBDIR
#
# At run time, we're (optionally) locating:
#
#     libpython.X.Y.so via RPATH_OPT 
#

ifeq "$(WITH_ZENOSS_PYTHON_DEVEL)" "yes"

    #---------------------------------------------------------------------------#
    # BUILD CORRECTNESS WARNING :-(
    #
    # Build-time dependencies upon an installed location are a bad habit we need
    # to break.  It defeats our ability to separate our build phase from
    # our install phase.  It also makes us generally prone to subtle build issues 
    # where backlevel programmatic interfaces bleed into our uplevel build because 
    # of linkage to a potentially downlevel install.
    #
    # We should be referencing natively installed devel packages or configure
    # the build to drop 3rd party headers and libs into a sandbox-relative
    # export directory parallel to src and obj.
    #
    # e.g.,  src
    #        export/include/Python.h
    #        export/lib/libpython2.7.so
    #        export/bin/python
    #        obj
    #---------------------------------------------------------------------------#

    PYTHON_INCDIR  = $(DESTDIR)$(ZENHOME)/include/python$(PYTHON_MAJ_MIN_VER)
    PYTHON_LIBDIR  = $(DESTDIR)$(ZENHOME)/lib

    # Make Zenoss more relocatable by removing hardcoded shared-libary
    # search path dependency upon /opt/zenoss/lib
    #
    # At runtime, have the dynamic loader search for libpython*.so relative to
    # where our program is installed (e.g., up one directory and down into lib).
    #
    #    bin/<program>
    #    lib/libpython*.so
    #
    # See: http://man7.org/linux/man-pages/man8/ld.so.8.html  (search on ORIGIN).
    
    LIBPYTHON_RPATH = '$$ORIGIN/../lib'
    ifeq "$(IGNORE_LD_LIBRARY_PATH)" "yes"
        # Ignore LD_LIBRARY_PATH when it comes to resolving the location of
        # libpython*.so at runtime.
        RPATH_OPT  = -Wl,-rpath,$(LIBPYTHON_RPATH) -Wl,-z,origin
    else
        # Allow LD_LIBRARY_PATH to influence the search path for shared libraries at
        # runtime.
        #
        # Adding --enable-new-dtags sets RPATH /and/ RUNPATH to the same value
        # within the ELF dynamic string table. The presence of RUNPATH causes RPATH 
        # to be ignored at runtime.  RUNPATH provides a mechanism for setting
        # default search directories that may be overridden by LD_LIBRARY_PATH
        # on the deployed system.
        #
        # See: http://blog.tremily.us/posts/rpath/
        RPATH_OPT  = -Wl,-rpath,$(LIBPYTHON_RPATH),--enable-new-dtags -Wl,-z,origin
    endif
else
    PYTHON_INCDIR  = /usr/include/python$(PYTHON_MAJ_MIN_VER)
    PYTHON_LIBDIR  = /usr/lib64
endif

CPPFLAGS = -I$(PYTHON_INCDIR)
LDLIBS   = -lpython$(PYTHON_MAJ_MIN_VER) -ldl

ifeq ($(shell uname), Darwin)
    LDFLAGS += -framework CoreFoundation -u _PyMac_Error
else
    LDFLAGS += -Xlinker -export-dynamic $(RPATH_OPT)
    LDLIBS  += -lpthread -lutil -lm
endif
LDFLAGS  += -L$(PYTHON_LIBDIR)


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
#---------------------------------------------------------------------------#
NEAREST_ZENMAGIC_MK := $(word 1,$(wildcard ./zenmagic.mk $(shell for slash in $$(echo $(abspath .) | sed -e "s|.*\(/obj/\)\(.*\)|\1\2|g" -e "s|.*\(/src/\)\(.*\)|\1\2|g" | sed -e "s|[^/]||g" -e "s|/|/ |g"); do string=$${string}../;echo $${string}zenmagic.mk; done | xargs echo)))

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
	if ! mkdir -p $@ ;then \
		echo "[$@] Error: Maybe you intended 'sudo make install' instead?" ;\
		exit 1 ;\
	else \
		chown -R $(INST_OWNER):$(INST_GROUP) $@ ;\
	fi

$(BUILD_DIR)/$(PROGRAM): $(BUILD_DIR)/$(PROGRAM).o
ifeq "$(DUMP_LD_LIBDEPS)" "yes"
	@$(call make-lib-depend,$^,$@)
endif
	$(LINK.c) $^ $(LOADLIBES) $(LDLIBS) -o $@

$(BUILD_DIR)/$(PROGRAM).o: | $(CHECKED_ENV)
$(BUILD_DIR)/$(PROGRAM).o: | $(PYTHON_INCDIR)
$(BUILD_DIR)/$(PROGRAM).o: | $(BUILD_DIR)
$(BUILD_DIR)/$(PROGRAM).o: $(PROGRAM).c
	$(call make-depend,$<,$@,$(subst .o,.d,$@))
	$(COMPILE.c) $(OUTPUT_OPTION) $<

BUILT_FILES = $(wildcard $(patsubst %,$(BUILD_DIR)/%,$(PROGRAM) $(PROGRAM).o $(PROGRAM).d $(PROGRAM).dlibs))
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

check: | $(BUILD_DIR)
check:
	@if [ ! -f "$(BUILD_DIR)/$(PROGRAM)" ]; then \
		echo "Unable to check $(PROGRAM).  Missing $(BUILD_DIR)/$(PROGRAM)." ;\
		echo $(LINE) ;\
		echo "Run 'make build' first" ;\
		echo ;\
		exit 1 ;\
	fi
ifeq "$(IGNORE_LD_LIBRARY_PATH)" "yes"
	@echo -en "Checking that $(BUILD_DIR)/$(PROGRAM) will ignore LD_LIBRARY_PATH: " ;\
	if $(READELF) --dynamic $(BUILD_DIR)/$(PROGRAM) | grep RUNPATH 1>/dev/null 2>&1 ;then \
		echo "[FAIL]" ;\
		echo $(LINE) ;\
		echo "The presence of RUNPATH in the dynamic string table of $(PROGRAM) indicates" ;\
		echo "the environment variable, LD_LIBRARY_PATH, will influence the dynamic loader's" ;\
		echo "search path for finding shared libraries required by $(PROGRAM)." ;\
		echo ;\
		echo "See: http://blog.tremily.us/posts/rpath/" ;\
		echo ;\
		echo "$(READELF) --dynamic $(BUILD_DIR)/$(PROGRAM) | grep RUNPATH" ;\
		$(READELF) --dynamic $(BUILD_DIR)/$(PROGRAM) | grep RUNPATH | xargs echo ;\
		echo ;\
		exit 1 ;\
	else \
		echo "[PASS]" ;\
	fi
else
	@echo -en "Checking that $(BUILD_DIR)/$(PROGRAM) will honor LD_LIBRARY_PATH: " ;\
	if $(READELF) --dynamic $(BUILD_DIR)/$(PROGRAM) | grep RUNPATH 1>/dev/null 2>&1	;then \
		echo "[PASS]" ;\
	else \
		if $(READELF) --dynamic $(BUILD_DIR)/$(PROGRAM) | grep RPATH ;then \
			echo "[FAIL]" ;\
			echo $(LINE) ;\
			echo "The presence of RPATH and absence of RUNPATH in the dynamic string table of $(PROGRAM) indicates" ;\
			echo "LD_LIBRARY_PATH will be ignored by the dynamic loader when searching for shared libraries" ;\
			echo "needed by $(PROGRAM)." ;\
			echo ;\
			echo "See: http://blog.tremily.us/posts/rpath/" ;\
			echo ;\
			echo "$(READELF) --dynamic $(BUILD_DIR)/$(PROGRAM) | grep PATH" ;\
			$(READELF) --dynamic $(BUILD_DIR)/$(PROGRAM) | grep PATH | sed -e "s| [ ]*| |g" ;\
			echo ;\
			exit 1 ;\
		else \
			echo "[PASS]" ;\
		fi ;\
	fi
endif
	@echo
	@echo -en "Checking list of shared libraries needed by $(BUILD_DIR)/$(PROGRAM) at runtime: " ;\
	if $(READELF) --dynamic $(BUILD_DIR)/$(PROGRAM) | grep NEEDED 1>/dev/null 2>&1	;then \
		echo ;\
		echo $(LINE) ;\
		$(READELF) --dynamic $(BUILD_DIR)/$(PROGRAM) | grep NEEDED |sed -e "s|.*\(NEEDED.*\)|\1|g" -e "s|)||g" -e "s| [ ]*| |g" ;\
	else \
		echo "[FAIL]" ;\
		echo "[$@] Error: Unable to dump the list of shared libraries required by $(BUILD_DIR)/$(PROGRAM)." ;\
	fi
	@echo
	@echo -en "Checking rpath and runpath elf attributes specified internally for $(BUILD_DIR)/$(PROGRAM): " ;\
	if $(READELF) --dynamic $(BUILD_DIR)/$(PROGRAM) | egrep "RPATH|RUNPATH" 1>/dev/null 2>&1 ;then \
		echo ;\
		echo $(LINE) ;\
		$(READELF) --dynamic $(BUILD_DIR)/$(PROGRAM) | egrep "RPATH|RUNPATH" ;\
	else \
		echo "[INFO]" ;\
		echo "Info: rpath and runpath attributes not set for $(BUILD_DIR)/$(PROGRAM)." ;\
		echo "      This means standard system lib paths and LD_LIBRARY_PATH will" ;\
		echo "      be used at runtime by the loader to resolve shared libarary dependencies." ;\
	fi
