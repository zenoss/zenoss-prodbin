#============================================================================
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
#============================================================================
.DEFAULT_GOAL := help # build|help

PROGRAM        = zensocket

# Define install-related attributes.

PROGRAM_PERMS   = 04750

# Define build-related attributes

blddir                ?= obj
bldtop                ?= $(blddir)
#bldtop                = obj
INCLUDE_SYSINC_DEPS    = no
INCLUDE_DEBUG_SYMS     = yes
REQUIRES_GCC           = 1
#IGNORE_LD_LIBRARY_PATH= no
# Dump out a PROGRAM's link-time dependencies to $(bldtop)/PROGRAM.dlibs
# This does not materially affect the build, but it does provide a means
# for understanding where certain library dependencies are creeping in.
DUMP_LD_LIBDEPS        = yes

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
    -include $(bldtop)/$(PROGRAM).d
endif

.PHONY: all build $(PROGRAM)
all build $(PROGRAM): $(bldtop)/$(PROGRAM)

$(bldtop):
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

$(bldtop)/$(PROGRAM): $(bldtop)/$(PROGRAM).o
ifeq "$(DUMP_LD_LIBDEPS)" "yes"
	$(call subshellcmd,MKDEPL,$^,$@)
endif
	$(call cmd,LINKC,$(LINK.c),$^,$(LOADLIBES),$(LDLIBS),$@)

$(bldtop)/$(PROGRAM).o: | $(PYTHON_INCDIR)
$(bldtop)/$(PROGRAM).o: | $(bldtop)
$(bldtop)/$(PROGRAM).o: $(PROGRAM).c
	$(call cmd,MKDEPC,$<,$@,$(subst .o,.d,$@))
	$(call cmd,CC,$(COMPILE.c),$(OUTPUT_OPTION),$<)

BUILT_FILES = $(wildcard $(patsubst %,$(bldtop)/%,$(PROGRAM) $(PROGRAM).o $(PROGRAM).d $(PROGRAM).dlibs))
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
	@if [ -d "$(bldtop)" ];then \
		count=`ls -a1 $(bldtop) 2>/dev/null|wc -l` ;\
		if ((count < 3 ));then \
			$(call cmd_noat,RMDIR,$(bldtop)) ;\
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
	@if [ ! -f "$(bldtop)/$(PROGRAM)" ]; then \
		echo "Unable to install $(PROGRAM).  Missing $(bldtop)/$(PROGRAM)." ;\
		echo $(LINE) ;\
		echo "Run 'make build' first" ;\
		echo ;\
		exit 1 ;\
	fi
	@if [ -z "$(_DESTDIR)$(bindir)" ]; then \
		echo "[$@] Error: The bindir variable must be set to something before I can install $(PROGRAM) there." ;\
		exit 1 ;\
	fi
	@($(call cmd_noat,INSTALL,$(bldtop)/$(PROGRAM),$(_DESTDIR)$(bindir)/$(PROGRAM),$(PROGRAM_PERMS),$(PROGRAM_OWNER),$(INST_GROUP))) ;\
	rc=$$? ;\
	if [ $${rc} -ne 0 ]; then \
		echo $(LINE) ;\
		install_woe=`$(INSTALL) -m $(PROGRAM_PERMS) -o $(PROGRAM_OWNER) $(bldtop)/$(PROGRAM) $(_DESTDIR)$(bindir) 2>&1` ;\
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

check: | $(bldtop)
check:
	@if [ ! -f "$(bldtop)/$(PROGRAM)" ]; then \
		echo "Unable to check $(PROGRAM).  Missing $(bldtop)/$(PROGRAM)." ;\
		echo $(LINE) ;\
		echo "Run 'make build' first" ;\
		echo ;\
		exit 1 ;\
	fi
ifeq "$(IGNORE_LD_LIBRARY_PATH)" "yes"
	@echo -en "Checking that $(bldtop)/$(PROGRAM) will ignore LD_LIBRARY_PATH: " ;\
	if $(READELF) --dynamic $(bldtop)/$(PROGRAM) | grep RUNPATH 1>/dev/null 2>&1 ;then \
		echo "[FAIL]" ;\
		echo $(LINE) ;\
		echo "The presence of RUNPATH in the dynamic string table of $(PROGRAM) indicates" ;\
		echo "the environment variable, LD_LIBRARY_PATH, will influence the dynamic loader's" ;\
		echo "search path for finding shared libraries required by $(PROGRAM)." ;\
		echo ;\
		echo "See: http://blog.tremily.us/posts/rpath/" ;\
		echo ;\
		echo "$(READELF) --dynamic $(bldtop)/$(PROGRAM) | grep RUNPATH" ;\
		$(READELF) --dynamic $(bldtop)/$(PROGRAM) | grep RUNPATH | xargs echo ;\
		echo ;\
		exit 1 ;\
	else \
		echo "[PASS]" ;\
	fi
else
	@echo -en "Checking that $(bldtop)/$(PROGRAM) will honor LD_LIBRARY_PATH: " ;\
	if $(READELF) --dynamic $(bldtop)/$(PROGRAM) | grep RUNPATH 1>/dev/null 2>&1	;then \
		echo "[PASS]" ;\
	else \
		if $(READELF) --dynamic $(bldtop)/$(PROGRAM) | grep RPATH ;then \
			echo "[FAIL]" ;\
			echo $(LINE) ;\
			echo "The presence of RPATH and absence of RUNPATH in the dynamic string table of $(PROGRAM) indicates" ;\
			echo "LD_LIBRARY_PATH will be ignored by the dynamic loader when searching for shared libraries" ;\
			echo "needed by $(PROGRAM)." ;\
			echo ;\
			echo "See: http://blog.tremily.us/posts/rpath/" ;\
			echo ;\
			echo "$(READELF) --dynamic $(bldtop)/$(PROGRAM) | grep PATH" ;\
			$(READELF) --dynamic $(bldtop)/$(PROGRAM) | grep PATH | sed -e "s| [ ]*| |g" ;\
			echo ;\
			exit 1 ;\
		else \
			echo "[PASS]" ;\
		fi ;\
	fi
endif
	@echo
	@echo -en "Checking list of shared libraries needed by $(bldtop)/$(PROGRAM) at runtime: " ;\
	if $(READELF) --dynamic $(bldtop)/$(PROGRAM) | grep NEEDED 1>/dev/null 2>&1	;then \
		echo ;\
		echo $(LINE) ;\
		$(READELF) --dynamic $(bldtop)/$(PROGRAM) | grep NEEDED | sed -e "s|.*\(NEEDED.*\)|\1|g" -e "s|)||g" -e "s| [ ]*| |g" ;\
	else \
		echo "[FAIL]" ;\
		echo "[$@] Error: Unable to dump the list of shared libraries required by $(bldtop)/$(PROGRAM)." ;\
	fi
	@echo
	@echo -en "Checking rpath and runpath elf attributes specified internally for $(bldtop)/$(PROGRAM): " ;\
	if $(READELF) --dynamic $(bldtop)/$(PROGRAM) | egrep "RPATH|RUNPATH" 1>/dev/null 2>&1 ;then \
		echo ;\
		echo $(LINE) ;\
		$(READELF) --dynamic $(bldtop)/$(PROGRAM) | egrep "RPATH|RUNPATH" ;\
	else \
		echo "[INFO]" ;\
		echo "Info: rpath and runpath attributes not set for $(bldtop)/$(PROGRAM)." ;\
		echo "      This means standard system lib paths and LD_LIBRARY_PATH will" ;\
		echo "      be used at runtime by the loader to resolve shared libarary dependencies." ;\
	fi
