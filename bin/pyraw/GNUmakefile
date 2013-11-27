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
# This should change to reference the python exported within
# the build sandbox rather than point to installed python.
zenoss_pydeveldir ?= $(_DESTDIR)$(prefix)

# Define install-related attributes.

PROGRAM_PERMS = 04750

# Define build-related attributes

blddir                   = obj
WITH_ZENOSS_PYTHON_DEVEL = no
INCLUDE_SYSINC_DEPS      = no
PYTHON_MAJ_MIN_VER       = 2.7
REQUIRES_GCC             = 1
IGNORE_LD_LIBRARY_PATH   = yes
# Dump out a PROGRAM's link-time dependencies to $(blddir)/PROGRAM.dlibs
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

    PYTHON_INCDIR  = $(zenoss_pydeveldir)/include/python$(PYTHON_MAJ_MIN_VER)
    PYTHON_LIBDIR  = $(zenoss_pydeveldir)/lib

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

here-targets  = installhere uninstallhere
ifeq "$(filter $(here-targets),$(MAKECMDGOALS))" ""
PROGRAM_OWNER = root
else
PROGRAM_OWNER = $(INST_OWNER)
endif

#============================================================================
# Build Targets
#============================================================================
ifneq "$(MAKECMDGOALS)" "clean"
    -include $(blddir)/$(PROGRAM).d
endif

.PHONY: all build $(PROGRAM)
all build $(PROGRAM): $(blddir)/$(PROGRAM)

$(blddir): 
	$(call cmd,MKDIR,$@)

$(_DESTDIR)$(bindir):
	@($(call cmd_noat,MKDIR,$@)) ;\
	rc=$$? ;\
	if [ $${rc} -ne 0 ] ; then \
		echo $(LINE) ;\
		echo "Maybe you intended 'sudo make install' or 'make installhere' instead?" ;\
		echo ;\
		exit $${rc} ;\
	else \
		$(call cmd_noat,CHOWN,,$(INST_OWNER),$(INST_GROUP),$@) ;\
		rc=$$? ;\
		if [ $${rc} -ne 0 ] ; then \
			exit $${rc} ;\
		fi ;\
	fi

$(blddir)/$(PROGRAM): $(blddir)/$(PROGRAM).o
ifeq "$(DUMP_LD_LIBDEPS)" "yes"
	$(call cmd,MKDEPL,$^,$@)
endif
	$(call cmd,LINKC,$(LINK.c),$^,$(LOADLIBES),$(LDLIBS),$@)

$(blddir)/$(PROGRAM).o: | $(CHECKED_ENV)
$(blddir)/$(PROGRAM).o: | $(PYTHON_INCDIR)
$(blddir)/$(PROGRAM).o: | $(blddir)
$(blddir)/$(PROGRAM).o: $(PROGRAM).c
	$(call cmd,MKDEPC,$<,$@,$(subst .o,.d,$@))
	$(call cmd,CC,$(COMPILE.c),$(OUTPUT_OPTION),$<)

BUILT_FILES = $(wildcard $(patsubst %,$(blddir)/%,$(PROGRAM) $(PROGRAM).o $(PROGRAM).d $(PROGRAM).dlibs))
.PHONY: clean
clean:
	@for target_file in $(BUILT_FILES) ;\
	do \
		$(call echol,"rm -f $${target_file}","RM     $${target_file}") ;\
		rm -rf "$${target_file}" ;\
		rc=$$? ;\
		if [ $${rc} -ne 0 ];then \
			exit $${rc} ;\
		fi ;\
	done
	@if [ -d "$(blddir)" ];then \
		count=`ls -a1 $(blddir) 2>/dev/null|wc -l` ;\
		if ((count < 3 ));then \
			$(call cmd_noat,RMDIR,$(blddir)) ;\
		fi ;\
	fi

.PHONY: mrclean distclean
mrclean distclean: clean dflt_component_distclean
	@if [ -e "$(_DESTDIR)$(bindir)/$(PROGRAM)" ];then \
		count=$(shell ls -a1 $(_DESTDIR)$(bindir) 2>/dev/null|wc -l) ;\
		if ((count >= 3 ));then \
			echo "You may also run 'make uninstall' to uninstall $(PROGRAM) from $(_DESTDIR)$(bindir)" ;\
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

.PHONY: install installhere
install installhere: | $(_DESTDIR)$(bindir)
install installhere:
	@if [ ! -f "$(blddir)/$(PROGRAM)" ]; then \
		echo "Unable to install $(PROGRAM).  Missing $(blddir)/$(PROGRAM)." ;\
		echo $(LINE) ;\
		echo "Run 'make build' first" ;\
		echo ;\
		exit 1 ;\
	fi
	@if [ -z "$(_DESTDIR)$(bindir)" ]; then \
		echo "[$@] Error: The bindir variable must be set to something before I can install $(PROGRAM) there." ;\
		exit 1 ;\
	fi
	@($(call cmd_noat,INSTALL,$(blddir)/$(PROGRAM),$(_DESTDIR)$(bindir)/$(PROGRAM),$(PROGRAM_PERMS),$(PROGRAM_OWNER),$(INST_GROUP))) ;\
	rc=$$? ;\
	if [ $${rc} -ne 0 ]; then \
		echo $(LINE) ;\
		install_woe=`$(INSTALL) -m $(PROGRAM_PERMS) -o $(PROGRAM_OWNER) $(blddir)/$(PROGRAM) $(_DESTDIR)$(bindir) 2>&1` ;\
		case $${install_woe} in \
			*cannot*overwrite*directory*) \
				echo "Whoa. You seem to have a directory where a file was expected?" ;\
				echo "Something went wrong or this is a hybrid dev environment." ;\
				echo "Abandoning install attempt." ;\
				echo $(LINE) ;\
				ls -ld $(_DESTDIR)$(bindir)/$(PROGRAM) ;\
				:;;\
			*cannot*change*ownership*) \
				echo "Here is what you attempted to overwrite:" ;\
				ls -ld $(_DESTDIR)$(bindir)/$(PROGRAM) ;\
				echo $(LINE) ;\
				echo "Maybe you intended 'sudo make install' or 'make installhere' instead?" ;\
				:;;\
			*Permission*denied*) \
				echo "Here is where you attempted to install:" ;\
				ls -ld $(_DESTDIR)$(bindir) ;\
				echo $(LINE) ;\
				echo "Maybe you intended 'sudo make install' or 'make installhere' instead?" ;\
				:;;\
			*) \
				echo "Please investigate." ;\
				:;;\
		esac ;\
		echo "[rc = $${rc}]";\
		exit ${rc} ;\
	fi

INSTFILES = $(wildcard $(patsubst %,$(_DESTDIR)$(bindir)/%,$(PROGRAM) $(PROGRAM).dSYM))
.PHONY: uninstall
uninstall:
	@for target_file in $(INSTFILES) ;\
	do \
		$(call echol,"rm -f $${target_file}","RM     $${target_file}") ;\
		rm -rf "$${target_file}" ;\
		rc=$$? ;\
		if [ $${rc} -ne 0 ];then \
			exit $${rc} ;\
		fi ;\
	done
	@count=`ls -a1 $(_DESTDIR)$(bindir) 2>/dev/null|wc -l` ;\
	if ((count < 3 ));then \
		($(call cmd_noat,RMDIR,$(_DESTDIR)$(bindir))) ;\
		rc=$$? ;\
		if [ $${rc} -ne 0 ] ; then \
			echo $(LINE) ;\
			echo "Maybe you intended 'sudo make $@' instead?" ;\
			echo ;\
			exit $${rc} ;\
		fi ;\
	fi

.PHONY: uninstallhere
uninstallhere: uninstall
	@if [ -d "$(heredir)" ];then \
		$(call cmd_noat,RMDIR,$(heredir)) ;\
	fi

.PHONY: help
help: dflt_component_help
	@echo Using common build idioms from $(NEAREST_ZENMAGIC_MK)
	@echo

check: | $(blddir)
check:
	@if [ ! -f "$(blddir)/$(PROGRAM)" ]; then \
		echo "Unable to check $(PROGRAM).  Missing $(blddir)/$(PROGRAM)." ;\
		echo $(LINE) ;\
		echo "Run 'make build' first" ;\
		echo ;\
		exit 1 ;\
	fi
ifeq "$(IGNORE_LD_LIBRARY_PATH)" "yes"
	@echo -en "Checking that $(blddir)/$(PROGRAM) will ignore LD_LIBRARY_PATH: " ;\
	if $(READELF) --dynamic $(blddir)/$(PROGRAM) | grep RUNPATH 1>/dev/null 2>&1 ;then \
		echo "[FAIL]" ;\
		echo $(LINE) ;\
		echo "The presence of RUNPATH in the dynamic string table of $(PROGRAM) indicates" ;\
		echo "the environment variable, LD_LIBRARY_PATH, will influence the dynamic loader's" ;\
		echo "search path for finding shared libraries required by $(PROGRAM)." ;\
		echo ;\
		echo "See: http://blog.tremily.us/posts/rpath/" ;\
		echo ;\
		echo "$(READELF) --dynamic $(blddir)/$(PROGRAM) | grep RUNPATH" ;\
		$(READELF) --dynamic $(blddir)/$(PROGRAM) | grep RUNPATH | xargs echo ;\
		echo ;\
		exit 1 ;\
	else \
		echo "[PASS]" ;\
	fi
else
	@echo -en "Checking that $(blddir)/$(PROGRAM) will honor LD_LIBRARY_PATH: " ;\
	if $(READELF) --dynamic $(blddir)/$(PROGRAM) | grep RUNPATH 1>/dev/null 2>&1	;then \
		echo "[PASS]" ;\
	else \
		if $(READELF) --dynamic $(blddir)/$(PROGRAM) | grep RPATH ;then \
			echo "[FAIL]" ;\
			echo $(LINE) ;\
			echo "The presence of RPATH and absence of RUNPATH in the dynamic string table of $(PROGRAM) indicates" ;\
			echo "LD_LIBRARY_PATH will be ignored by the dynamic loader when searching for shared libraries" ;\
			echo "needed by $(PROGRAM)." ;\
			echo ;\
			echo "See: http://blog.tremily.us/posts/rpath/" ;\
			echo ;\
			echo "$(READELF) --dynamic $(blddir)/$(PROGRAM) | grep PATH" ;\
			$(READELF) --dynamic $(blddir)/$(PROGRAM) | grep PATH | sed -e "s| [ ]*| |g" ;\
			echo ;\
			exit 1 ;\
		else \
			echo "[PASS]" ;\
		fi ;\
	fi
endif
	@echo
	@echo -en "Checking list of shared libraries needed by $(blddir)/$(PROGRAM) at runtime: " ;\
	if $(READELF) --dynamic $(blddir)/$(PROGRAM) | grep NEEDED 1>/dev/null 2>&1	;then \
		echo ;\
		echo $(LINE) ;\
		$(READELF) --dynamic $(blddir)/$(PROGRAM) | grep NEEDED |sed -e "s|.*\(NEEDED.*\)|\1|g" -e "s|)||g" -e "s| [ ]*| |g" ;\
	else \
		echo "[FAIL]" ;\
		echo "[$@] Error: Unable to dump the list of shared libraries required by $(blddir)/$(PROGRAM)." ;\
	fi
	@echo
	@echo -en "Checking rpath and runpath elf attributes specified internally for $(blddir)/$(PROGRAM): " ;\
	if $(READELF) --dynamic $(blddir)/$(PROGRAM) | egrep "RPATH|RUNPATH" 1>/dev/null 2>&1 ;then \
		echo ;\
		echo $(LINE) ;\
		$(READELF) --dynamic $(blddir)/$(PROGRAM) | egrep "RPATH|RUNPATH" ;\
	else \
		echo "[INFO]" ;\
		echo "Info: rpath and runpath attributes not set for $(blddir)/$(PROGRAM)." ;\
		echo "      This means standard system lib paths and LD_LIBRARY_PATH will" ;\
		echo "      be used at runtime by the loader to resolve shared libarary dependencies." ;\
	fi
