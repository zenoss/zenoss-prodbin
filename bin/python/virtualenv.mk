#=============================================================================
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
# TODO: Add installex, uninstallex.
#       Kill all raw echos.  This doesn't get logged.  Use echol, etc.
#       Tersify the uninstall better now that $${shell} vars are supported.
#       Why are CHOWN's not logging?
#=============================================================================
.DEFAULT_GOAL := help # all|build|devinstall|help|install

#---------------------------------------------------------------------------#
# At the component level, use this makefile to do standard things.
#
#    make <target>, where target is one of the following:
#
#    build,   clean
#    install, uninstall
#    help,    settings
#
# However, when building at the application level, the expected build flow 
# would be:
#
#    export         # Build virtualized python into a sandbox-relative
#                   # area visible by other python-hungry components that
#                   # need either python or related headers and libs.
#
#    # Exported python is subsequently used by other components we build,   
#    # possibly writing into the exported python's lib/pythonX.Y directory. 
#
#    relocate       # Mutate the exported python so it is relocatable to
#                   # another area of the filesystem.
#
#    installex      # Install exported python to $(DESTDIR)$(prefix)
#                   # e.g., /opt/zenoss/{bin,lib,include}.
#---------------------------------------------------------------------------#

#============================================================================
# Build component configuration.
#
# Beware of trailing spaces.
# Don't let your editor turn tabs into spaces or vice versa.
#============================================================================
COMPONENT          = python

# Fetch required python version from zenmagic.mk.  Use this token
# to segregate output in our build directory structure.  This allows us
# to play with several different versions of python at a time.
#
# e.g., 2.7.3
#
python_version = $(strip $(REQD_PYTHON_MIN_VER))

# Trigger zenmagic.mk to have python affinity while building this component.
REQUIRES_PYTHON    = 1

# Specify the reference python used by virtualenv when bootstrapping our 
# application-centric python.  This definition is typically pulled from 
# zenmagic.mk but can be overridden as an environment variable.
#
# Virtualenv offers the advantage of almost 0-build time since it either 
# copies or symlinks files from a reference python already installed on the 
# system.  From a packaging perspective, relocating a virtualenv is still
# novel and adventurous.  See:
# http://www.alexhudson.com/2013/05/24/packaging-a-virtualenv-really-not-relocatable/
#
# e.g., /usr/bin/python2.7
#
VIRTUALENV_PYTHON ?= $(SYS_PYTHON)

# Give our 'isolated python' visibility onto the system's site-packages
# directories at build time and, by extension, runtime on a deployed 
# system.  So things like os.py will be symlinked to the reference 
# python's os.py.  For example:
#
#    /opt/zenoss/lib/python2.7/os.py -> /usr/lib64/python2.7/os.py
#
# The virtue is reduced deployment footprint and we get out of the 
# business of having to manage / upgrade these prerequisites internally.
#
# The vice is that we lose some self-containment of the build environment 
# and need to exercise discipline with what we install, python-wise, on the 
# build machine.  We also need to be mindful of specifying any related external
# dependencies in our packaging.  Otherwise our symlinks will be pointing
# at dark matter on a deployed system.
#
USE_SYSTEM_SITE_PACKAGES = yes

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
    $(warning "Missing zenmagic.mk")
    $(warning "Unable to find our file of build idioms in the current or parent directories.")
    $(error   "A fully populated src tree usually resolves that.")
else
    include $(NEAREST_ZENMAGIC_MK)
endif

#---------------------------------------------------------------------------#
# Variables for this makefile
#---------------------------------------------------------------------------#
bldtop = build

# Specify the sandbox-relative export directory where our virtualenv'd
# python is made available to other parts of the build.
# (Enables separation of build and install targets.)
#
# When building zenoss from the top, this may be overridden to something
# more global like:
#
#            sb/src/{core,metric-service,zproxy,...}
#             |
# exportdir = +/tools/x86_64/$(python_pkg)/{bin,lib,include}
#
exportdir = $(bldtop)/export/$(python_pkg)

# Python is an external dependency which we currently fold into our
# build and packaging.  Underscore that relationship in our build-time 
# directory structure as a low-tech means for auditing same.
#
# Specify the directory where we perform a calibration build of
# our virtualenv'd python.
#
externaldir = $(bldtop)/external

# Installing 'python' is relatively easy.  However uninstalling is another
# matter.  Beyond the python interpreter itself, there are over 4000 files
# spread across 3 directories that embody the python footprint.  We get around
# some of the install and uninstall issues by creating manifests of the 
# associated files, links, and directories.  We can iterate across these lists
# to enforce file ownership or perform surgical uninstalls.
#
manifesttop    = $(heredir)/manifests
manifestdir    = $(manifesttop)/$(python_pkg)
files_manifest = $(abspath $(manifestdir)/files.manifest)
links_manifest = $(abspath $(manifestdir)/links.manifest)
dirs_manifest  = $(abspath $(manifestdir)/dirs.manifest)

# Fetch a truncated version of required python.  Use this when
# creating convenience symlinks (e.g., python -> python2.7).
#
# e.g., Convert 2.7.3 into 2.7
python_version_maj_min := $(shell echo $(python_version) | cut -d. -f1-2)

# Attributes associated with the python we're isolating.
python         = Python
python_flavor  = venv   # Allow segregation from src-built python.
_python_flavor = $(strip $(python_flavor))
python_pkg     = $(python)-$(python_version)-$(_python_flavor)

# Convenience macros for key files we build or reference.
program           = python
built_python     := $(externaldir)/$(python_pkg)/bin/$(program)
built_python_dir := $(externaldir)/$(python_pkg)
built_target     := $(built_python)

# Dropping --system-site-packages adds this file:
# ./lib/python2.7/no-global-site-packages.txt
ifeq "$(USE_SYSTEM_SITE_PACKAGES)" "yes"
    VIRTUALENV_OPTS += --system-site-packages
endif

#============================================================================
# Subset of standard build targets our makefiles should implement.  
#
# See: http://www.gnu.org/prep/standards/html_node/Standard-Targets.html#Standard-Targets
#============================================================================

#---------------------------------------------------------------------------#
# Build Targets
#---------------------------------------------------------------------------#
.PHONY: all build
all build: python

$(built_python_dir) $(manifestdir):
	$(call cmd,MKDIR,$@)

.PHONY: python
python: $(built_python)

$(built_python): | $(CHECKED_ENV) $(built_python_dir)
	$(call cmd,VIRTUALENV,$(VIRTUALENV_OPTS),$(VIRTUALENV_PYTHON),$(built_python_dir))

$(_DESTDIR)$(prefix):
	@($(call cmd_noat,MKDIR,$@)) ;\
	set -x -v ;\
	rc=$$? ;\
	if [ $${rc} -ne 0 ] ; then \
		echo $(LINE) ;\
		echo "Maybe you intended 'sudo make install' or 'make installhere' instead?" ;\
		echo ;\
		exit $${rc} ;\
	else \
		($(call cmd_noat,CHOWN,,$(INST_OWNER),$(INST_GROUP),$@)) ;\
		rc=$$? ;\
		if [ $${rc} -ne 0 ] ; then \
			exit $${rc} ;\
		fi ;\
	fi

.PHONY: install
install: $(files_manifest) $(links_manifest) $(dirs_manifest)
install: | $(_DESTDIR)$(prefix)
	@if [ ! -f "$(built_python)" ]; then \
		echo "Unable to install $(program).  Missing $(built_python)." ;\
		echo $(LINE) ;\
		echo "Run 'make build' first" ;\
		echo ;\
		exit 1 ;\
	fi
	@if ($(call cmd_noat,VIRTUALENV,$(VIRTUALENV_OPTS),$(VIRTUALENV_PYTHON),$(_DESTDIR)$(prefix))) ; then \
		cd $(_DESTDIR)$(bindir)
		if [ -f python$(python_version_maj_min) ] ;then \
			if [ ! -L python ]; then \
				if ($(call cmd_noat,SYMLINK,python$(python_version_maj_min),python)) ; then \
					echo "Unable to create python symlink." ;\
					exit 1 ;\					
				fi ;\
			fi ;\
		else \
			echo "Missing $(_DESTDIR)$(bindir)/python$(python_version_maj_min)" ;\
			echo "Unable to create python symlink." ;\
			exit 1 ;\
		fi ;\
		saveIFS=$(IFS) ;\
		IFS=$(echo -en "\n\b") ;\
		while read installedFile ;\
		do \
			_installedFile=$(_DESTDIR)$${installedFile} ;\
			if [ -f "$${_installedFile}" -o -L "$${_installedFile}" ];then \
				if ! ($(call cmd_noat,CHOWN,,$(INST_OWNER),$(INST_GROUP),$${_installedFile})) ;then \
					IFS=$${saveIFS} ;\
					exit 1 ;\
				fi ;\
			fi ;\
		done < $(files_manifest) ;\
		while read installedLink ;\
		do \
			_installedLink=$(_DESTDIR)$${installedLink} ;\
			if [ -L "$${_installedLink}" ];then \
				if ! ($(call cmd_noat,CHOWN_LINK,$(INST_OWNER),$(INST_GROUP),$${_installedLink})) ;then \
					IFS=$${saveIFS} ;\
					exit 1 ;\
				fi ;\
			fi ;\
		done < $(links_manifest) ;\
		while read installedDir ;\
		do \
			_installedDir=$(_DESTDIR)$${installedDir} ;\
			if [ -d "$${_installedDir}" ];then \
				if ! ($(call cmd_noat,CHOWN,,$(INST_OWNER),$(INST_GROUP),$${_installedDir})) ;then \
					IFS=$${saveIFS} ;\
					exit 1 ;\
				fi ;\
			fi ;\
		done < $(dirs_manifest) ;\
		IFS=$${saveIFS} ;\
	else \
		echo "Error installing $(program) under $(_DESTDIR)$(prefix) using virtualenv." ;\
		echo "Maybe you intended 'sudo make install' instead?" ;\
		exit 1 ;\
	fi

#---------------------------------------------------------------------------#
# Attempt a sandbox-relative install.  If that fails, then we should probably
# fix that before attempting a 'sudo make install' onto the system.
#
# This is also our mechanism for creating manifests prior to a system-level 
# install.  Manifests give us traceability of files associated with a 
# component and surgical uninstall ability.
#---------------------------------------------------------------------------#
.PHONY: installhere
installhere: 
	@if [ ! -f "$(built_python)" ]; then \
		echo "Unable to install $(program).  Missing $(built_python)." ;\
		echo $(LINE) ;\
		echo "Run 'make build' first" ;\
		echo ;\
		exit 1 ;\
	fi
	@if ($(call cmd_noat,VIRTUALENV,$(VIRTUALENV_OPTS),$(VIRTUALENV_PYTHON),$(_DESTDIR)$(prefix))) ; then \
		cd $(abspath $(_DESTDIR)$(bindir)) ;\
		if [ -f python$(python_version_maj_min) ] ;then \
			if [ ! -L python ]; then \
				if ($(call cmd_noat,SYMLINK,python$(python_version_maj_min),python)) ; then \
					echo "Unable to create python symlink." ;\
					exit 1 ;\					
				fi ;\
			fi ;\
		else \
			echo "Missing $(_DESTDIR)$(bindir)/python$(python_version_maj_min)" ;\
			echo "Unable to create python symlink." ;\
			exit 1 ;\
		fi ;\
	else \
		echo "Error installing $(program) under $(_DESTDIR)$(prefix) using virtualenv." ;\
		echo "Maybe you intended 'sudo make install' instead?" ;\
		exit 1 ;\
	fi
	$(call cmd,CHOWN,-R,$(INST_OWNER),$(INST_GROUP),$(abspath $(_DESTDIR)))

#---------------------------------------------------------------------------#
# Export the python interpreter, headers, and libs to an area under the 
# build tree where subsequent portions of the build can refer and use.  This 
# is key for separating our build and install targets at the product-level 
# source build.
#---------------------------------------------------------------------------#
exportto := $(exportdir)$(prefix)
.PHONY: export
export: $(exportto)

$(exportto):
	@if [ ! -f "$(built_python)" ]; then \
		echo "Unable to export $(program).  Missing $(built_python)." ;\
		echo $(LINE) ;\
		echo "Run 'make build' first" ;\
		echo ;\
		exit 1 ;\
	fi
	@if ($(call cmd_noat,VIRTUALENV,$(VIRTUALENV_OPTS),$(VIRTUALENV_PYTHON),$@)) ;then \
		cd $(abspath $@/bin) ;\
		if [ -f python$(python_version_maj_min) ] ;then \
			if [ ! -L python ]; then \
				if ($(call cmd_noat,SYMLINK,python$(python_version_maj_min),python)) ; then \
					echo "Unable to create python symlink." ;\
					exit 1 ;\					
				fi ;\
			fi ;\
		else \
			echo "Missing $@/bin/python$(python_version_maj_min)" ;\
			echo "Unable to create python symlink." ;\
			exit 1 ;\
		fi ;\
	else \
		echo "Error installing $(program) under $@ using virtualenv." ;\
		exit 1 ;\
	fi

#---------------------------------------------------------------------------#
# Some virtualenv fu so our exported python can be relocated to the final
# install prefix.
#---------------------------------------------------------------------------#
.PHONY: relocatable relocate
relocatable relocate:| $(exportto)
	$(call cmd,RELOCATABLE,$(exportto))

#---------------------------------------------------------------------------#
# Target used to trigger an install of the python package to a 
# sandbox-relative location:
#
#    ./here/opt/zenoss/{bin,lib,include}
#
# before attempting a system level install:
#
#    /opt/zenoss/{bin,lib,include}
#---------------------------------------------------------------------------#
$(heredir)$(bindir)/python:
	@$(MAKE) --no-print-directory installhere

#---------------------------------------------------------------------------#
# Targets to create manifests of all the associated files, links, and 
# directories that make up the installed python footprint.  These are used 
# to audit comprises the installed package and to enable robust installs and 
# surgical uninstalls.
#
#
# Here we call into subshellcmd because the underlying manifest creation
# macros employ a subshell which is not tolerated well by the cmd macro.
# You'll get an error, otherwise, from echo because the subshell is not quoted.
#---------------------------------------------------------------------------#
%/files.manifest: $(heredir)$(bindir)/python | $(manifestdir)
	@$(call subshellcmd,MK_F_MANIFEST,$(heredir),$(prefix),$@)

%/links.manifest: $(heredir)$(bindir)/python | $(manifestdir)
	@$(call subshellcmd,MK_L_MANIFEST,$(heredir),$(prefix),$@)

%/dirs.manifest: $(heredir)$(bindir)/python | $(manifestdir)
	@$(call subshellcmd,MK_D_MANIFEST,$(heredir),$(prefix),$(_DESTDIR)$(prefix),$@)
	$(call cmd,CHOWN,-R,$(INST_OWNER),$(INST_GROUP),$(manifestdir))

.PHONY: manifests
manifests: $(files_manifest) $(links_manifest) $(dirs_manifest)


#---------------------------------------------------------------------------#
# Manifest-based uninstall.
#---------------------------------------------------------------------------#
#if ! $(call cmd_noat,RM,$(_DESTDIR)$${delFile}) ;then
.ONESHELL: uninstall
.PHONY: uninstall
uninstall: 
	@if [ ! -d "$(_DESTDIR)$(prefix)" ];then
		echo
		echo "$(_DESTDIR)$(prefix) not found.  Nothing to uninstall."
		echo
	else
		if [ ! -w "$(_DESTDIR)$(prefix)" ];then
			echo not writable
			echo
			echo "Unable to remove files under $(_DESTDIR)$(prefix)"
			echo "Maybe you intended 'sudo make uninstall' instead?"
			echo
		else
			count=`ls -a1 $(_DESTDIR)$(prefix) 2>/dev/null | wc -l`
			if ((count<=2));then
				echo
				echo "Nothing to uninstall under $(_DESTDIR)$(prefix)"
				echo
				exit 0
			fi
			if [ ! -f "$(files_manifest)" -o ! -f "$(dirs_manifest)" ];then
				echo
				echo "Unable to uninstall without a manifest of installed files and directories."
				echo
				echo "Please run: 'make build manifests uninstall'"
				echo
				exit 1
			else
				saveIFS=$(IFS)
				IFS=$(echo -en "\n\b")
				while read delFile
				do
					_delFile=$(_DESTDIR)$${delFile}
					if [ -f "$${_delFile}" -o -L "$${_delFile}" ];then
						$(call echol,"rm -f $${_delFile}","RM     $${_delFile}")
						rm -rf "$${_delFile}"
						rc=$$?
						if [ $${rc} -ne 0 ];then
							echo "Error removing $${_delFile}"
							echo "Giving up on $@."
							echo "Maybe you intended 'sudo make uninstall' instead?"
							IFS=$${saveIFS}
							exit $${rc}
						fi
					fi
				done < $(files_manifest)
				while read delLink
				do
					_delLink=$(_DESTDIR)$${delLink}
					if [ -L "$${_delLink}" -o -f "$${_delLink}" ];then
						$(call echol,"rm -f $${_delLink}","RMLINK $${_delLink}")
						rm -rf "$${_delLink}"
						rc=$$?
						if [ $${rc} -ne 0 ];then
							echo "Error removing $${_delLink}"
							echo "Giving up on $@."
							echo "Maybe you intended 'sudo make uninstall' instead?"
							IFS=$${saveIFS}
							exit $${rc}
						fi
					fi
				done < $(links_manifest)
				if find $(_DESTDIR)$(prefix) -type f -o -type l 2>/dev/null 1>&2 ;then
					while read delDir
					do
						case $${delDir} in
							/|/usr|/opt|/etc|/var|/bin|/sbin|/lib|/home|/root|/sys|/dev|/boot)	
								:;;
							*)
								_delDir=$(_DESTDIR)$${delDir}
								if [ -d "$${_delDir}" ];then
									count=`ls -a1 $${_delDir} 2>/dev/null | wc -l`
									if ((count<=2));then
										$(call echol,"rm -rf $${_delDir}","RMDIR  $${_delDir}")
										rm -rf "$${_delDir}"
										rc=$$?
										if [ $${rc} -ne 0 ];then
											echo "Error removing $${_delDir}"
											echo "   rm -rf $${_delDir}"
											echo "Giving up on $@."
											echo "Maybe you intended 'sudo make uninstall' instead?"
											echo "Otherwise you will need to manually remove python from $(_DESTDIR)$(prefix)"
											IFS=$${saveIFS}
											exit $${rc}
										fi
									else
										$(call echol, "Sipping $${_delDir}.  Non-empty.","SKIP    $${_deldir}.  Non-empty.")
									fi
								fi
								;;
						esac
					done < $(dirs_manifest)
				fi
				IFS=$${saveIFS}
				if [ -d "$(heredir)" ];then
					if ! $(MAKE) --no-print-directory uninstallhere ;then
						exit 1
					fi
				fi
			fi
		fi
	fi

.PHONY: help
help: dflt_component_help

# Variables of interest that we dump out if you run 'make settings'
# This will give you an idea of how the build will behave as currently
# configured.
control_variables  = bldtop 
control_variables += CHECKED_ENV
control_variables += DESTDIR
control_variables += exportdir 
control_variables += exportto 
control_variables += INST_GROUP 
control_variables += INST_OWNER 
control_variables += NEAREST_ZENMAGIC_MK 
control_variables += prefix
control_variables += python_pkg 
control_variables += python_version 
control_variables += USE_SYSTEM_SITE_PACKAGES 
control_variables += VIRTUALENV_OPTS 
control_variables += VIRTUALENV_PYTHON 
control_variables += with_virtualenv

.PHONY: settings
settings: 
	$(call show-vars,"Current makefile settings:",$(control_variables))

.PHONY: clean
clean:
	@if [ -d "$(bldtop)" ];then \
		if [ "$(abspath $(bldtop))" != "$(abspath $(srcdir))" ];then \
			($(call cmd_noat,RMDIR,$(bldtop))) ;\
			rc=$$? ;\
			if [ $${rc} -ne 0 ] ; then \
				echo $(LINE) ;\
				echo "Problem removing $(bldtop)." ;\
				echo ;\
				exit $${rc} ;\
			fi ;\
		else \
			$(call echol,"Error: Ignorning request to remove the build directory which is") ;\
			$(call echol,"       currently the same as your source directory.") ;\
			$(call echol,$(LINE)) ;\
			$(call echol,"       bldtop $(abspath $(bldtop))") ;\
			$(call echol,"       srcdir $(abspath $(srcdir))") ;\
		fi ;\
	fi

.PHONY: mrclean
mrclean distclean: installed_python = $(_DESTDIR)$(bindir)/$(program)
mrclean distclean: clean dflt_component_distclean
	@for delfile in $(_COMPONENT).log ;\
	do \
		if [ -f "$${delfile}" ];then \
			$(call cmd_noat,RM,$${delfile}) ;\
		fi ;\
	done

.PHONY: uninstallhere
uninstallhere:
	@if [ -d "$(heredir)" ];then \
		$(call cmd_noat,RMDIR,$(heredir)) ;\
	fi

check:
	@if [ ! -f "$(built_target)" ]; then \
		echo "Unable to check $(program).  Missing $(built_target)." ;\
		echo $(LINE) ;\
		echo "Run 'make build' first" ;\
		echo ;\
		exit 1 ;\
	fi
	@echo
	@echo -en "Checking list of shared libraries needed by $(built_target) at runtime: " ;\
	if $(READELF) --dynamic $(built_target) | grep NEEDED 1>/dev/null 2>&1	;then \
		echo ;\
		echo $(LINE) ;\
		$(READELF) --dynamic $(built_target) | grep NEEDED |sed -e "s|.*\(NEEDED.*\)|\1|g" -e "s|)||g" -e "s| [ ]*| |g" ;\
	else \
		echo "[FAIL]" ;\
		echo "[$@] Error: Unable to dump the list of shared libraries required by $(built_target)." ;\
	fi
	@echo
	@echo -en "Checking rpath and runpath elf attributes specified internally for $(built_target): " ;\
	if $(READELF) --dynamic $(built_target) | egrep "RPATH|RUNPATH" 1>/dev/null 2>&1 ;then \
		echo ;\
		echo $(LINE) ;\
		$(READELF) --dynamic $(built_target) | egrep "RPATH|RUNPATH" ;\
	else \
		echo "[INFO]" ;\
		echo "Info: rpath and runpath attributes not set for $(built_target)." ;\
		echo "      This means standard system lib paths and LD_LIBRARY_PATH will" ;\
		echo "      be used at runtime by the loader to resolve shared libarary dependencies." ;\
	fi
