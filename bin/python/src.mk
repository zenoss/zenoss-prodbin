#=============================================================================
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
#=============================================================================
# TODO: See notes at end of file.
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
#    installex      # Install exported python to $(DESTDIR)$(prefix)
#                   # e.g., /opt/zenoss/{bin,lib,include}.
#---------------------------------------------------------------------------#

#============================================================================
# Build component configuration.
#
# Beware of trailing spaces.
# Don't let your editor turn tabs into spaces or vice versa.
#============================================================================
COMPONENT = python

# Fetch required python version from zenmagic.mk.  Use this token
# to specify which Python-x.y.z.tgz source archive to download.
#
# e.g., 2.7.3
#
python_version = $(strip $(REQD_PYTHON_MIN_VER))

# The starting point for building python from source is acquiring the
# source *.tgz archive off the net.  Specify some url's that host the source 
# archive.  
#
# (You may also stage a source archive local to your python sandbox
# and precedence will be given to that over the remote python archive.)
#
dnstream_src_url = http://zenpip.zendev.org/packages
upstream_src_url = http://www.python.org/ftp/python/$(python_version)
prefer_dnstream  = yes # express preference for dnstream over upstream url

# Specify if libpython is statically or dynamically linked against
# source-built python.
SHARED_LIBPYTHON = yes

# Decide if the LD_LIBRARY_PATH environment variable will influence
# the shared library loader at runtime when our dynamically linked python
# interpreter is invoked and the loader is resolving the path to libpythonX.Y.so.
ignore_LD_LIBRARY_PATH = yes

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

# Specify the sandbox-relative place to install python/headers/libs for 
# subsequent use during the larger build.  Enables separation of build and
# install targets.
exportdir = $(bldtop)/export/$(python_pkg)

# Python is an external dependency which we currently fold into our
# build and packaging.  Underscore that relationship in our build-time 
# directory structure as a low-tech means for auditing same.
#
# Specify the directory where we download and build python from source.
externaldir = $(bldtop)/external

# Installing 'python' is relatively easy.  However uninstalling is another
# matter.  Beyond the built python interpreter itself, there are over 4000 files
# spread across 3 directories that embody the python footprint.  We get around
# some of the install and uninstall short-comings in the upstream python 
# build by creating a manifest of the installed files, links, and directories.
#
# Specify the directory where the python manifests reside.
manifesttop    = $(heredir)/manifests
manifestdir    = $(manifesttop)/$(python_pkg)
files_manifest = $(abspath $(manifestdir)/files.manifest)
links_manifest = $(abspath $(manifestdir)/links.manifest)
dirs_manifest  = $(abspath $(manifestdir)/dirs.manifest)

# e.g., Convert 2.7.3 into 2.7
python_version_maj_min := $(shell echo $(python_version) | cut -d. -f1-2)

_prefer_dnstream = $(strip $(prefer_dnstream))

# Since this usually involves pulling the *.tgz from
# an internal or external network, provide a means for checking the integrity
# of the *.tgz before proceeding with the build.
check_md5 = yes

ifeq "$(check_md5)" "yes"
Python-2.7.2.tgz_md5  = 076597d321e2250756f9ba9d7d5ef99f
# That 'zd5' lurking there is for our internally patched python source archive;
# more of a legacy play in case we backport the new bldenv to 4.x.
Python-2.7.2.tgz_zd5  = 0ddfe265f1b3d0a8c2459f5bf66894c7
Python-2.7.3.tgz_md5  = 2cf641732ac23b18d139be077bd906cd
Python-2.7.4.tgz_md5  = 592603cfaf4490a980e93ecb92bde44a
Python-2.7.5.tgz_md5  = b4f01a1d0ba0b46b05c73b2ac909b1df
#Python-2.7.6.tgz_md5 = http://www.python.org/download/releases/2.7.6/
endif

# Attributes associated with the python src tgz we're processing.
python                         = Python
python_pkg                     = $(python)-$(python_version)
python_pkg_tgz                 = $(python_pkg).tgz
$(python_pkg_tgz)_local_path   = ./$(python_pkg).tgz
$(python_pkg_tgz)_dnstream_url = $(dnstream_src_url)/$(python_pkg).tgz
$(python_pkg_tgz)_upstream_url = $(upstream_src_url)/$(python_pkg).tgz

# Convenience macros for key files we build or reference.
program           = python
built_python     := $(externaldir)/$(python_pkg)/$(program)
built_target     := $(built_python)
python_configure := $(externaldir)/$(python_pkg)/configure
python_makefile  := $(externaldir)/$(python_pkg)/Makefile

#---------------------------------------------------------------------------#
# Work-around a potential issue with hard-links failing in our vagrant dev 
# environment.  If hardlinks are not supported on the filesystem then you'll 
# get a failure in the upstream python build in this rule:
#
#    Python-x.y.z/Makefile
#    ---------------------
#    490 libpython$(VERSION).so: $(LIBRARY_OBJS)
#              ..
# >> 493       $(LN) -f $(INSTSONAME) $@; \
#---------------------------------------------------------------------------#
LN           = ln -s
PKG_CONFIG   = /usr/bin/pkg-config

#---------------------------------------------------------------------------#
# Configure-time options common to statically and dynamically linked python.
#
# Specifying:
#
# 1. system pkg-config 
# 2. version of ln that works when hardlinks don't (e.g., some vagrant dev VMs).
# 3. install prefix (e.g., /opt/zenoss)
# 4. place where python modules live (e.g., /opt/zenoss/lib/{pythonX.Y}
#---------------------------------------------------------------------------#
common_opts := PKG_CONFIG=$(PKG_CONFIG) LN="$(LN)" --prefix=$(prefix) --libdir=$(prefix)/lib

#---------------------------------------------------------------------------#
# Make Zenoss more relocatable by removing hardcoded shared-library
# search path dependency upon /opt/zenoss/lib.
#
# At runtime, have the dynamic loader search for libpython*.so relative to
# where python is installed (e.g., up one directory and down into ./lib).
# via link-time $ORIGIN/../lib idiom:
#
#    bin/python
#    lib/libpython*.so
#
# See: http://man7.org/linux/man-pages/man8/ld.so.8.html  (search on ORIGIN).
#
# NB: Jump through some hoops so LDFLAGS ends up as:
#
#         LDFLAGS = .. -Wl,-rpath,\$$ORIGIN/../lib
#
#     since python's configure script needs that apparently:
#     See: http://bugs.python.org/issue5201
#
# This is a departure from Zenoss 4.x where we used:
#
#         LDFLAGS = '-Wl,-R$$(prefix)/lib'
#
# which essentially hardcodes the location of libpython to /opt/zenoss/lib.
#---------------------------------------------------------------------------#
ORIGIN = '\$$$$ORIGIN'
LIBPYTHON_RPATH = '$(ORIGIN)/../lib'
ifeq "$(ignore_LD_LIBRARY_PATH)" "yes"
    # Ignore LD_LIBRARY_PATH when it comes to resolving the location of
    # libpython*.so at runtime.
    RPATH_OPT = -Wl,-rpath,$(LIBPYTHON_RPATH) -Wl,-z,origin
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
    RPATH_OPT = -Wl,-rpath,$(LIBPYTHON_RPATH),--enable-new-dtags -Wl,-z,origin
endif
# Squelch nuisance warnings in the upstream build that are not actionable to us.
python_CFLAGS = -Wno-unused-but-set-variable
python_LDFLAGS = $(RPATH_OPT)

ifeq "$(SHARED_LIBPYTHON)" "yes"
    $(python_pkg)_configure_opts = $(common_opts) --enable-shared
else
    $(python_pkg)_configure_opts = $(common_opts)
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

$(externaldir) $(manifestdir):
	$(call cmd,MKDIR,$@)

$(externaldir)/%.tgz : local_path   = $($(@F)_local_path)
$(externaldir)/%.tgz : upstream_url = $($(@F)_upstream_url)
$(externaldir)/%.tgz : dnstream_url = $($(@F)_dnstream_url)
.ONESHELL: $(externaldir)/%.tgz
$(externaldir)/%.tgz : | $(externaldir)
	@if [ -f "$(local_path)" ];then
		$(call cmd_noat,CP,$(local_path),$@)
		rc=$$?
		if [ $${rc} -ne 0 ];then
			exit $${rc}
		fi
	else
ifeq "$(_prefer_dnstream)" "yes"
		for src_tgz_url in $(dnstream_url) $(upstream_url)
else
		for src_tgz_url in $(upstream_url) $(dnstream_url)
endif
		do
			($(call cmd_noat,CURL,$@,$${src_tgz_url}))
			rc=$$?
			if [ $${rc} -eq 0 ];then
				break
			fi
		done
	fi
	if [ ! -f "$@" ];then
		echo "Unable to stage $@"
		exit 1
	fi

#---------------------------------------------------------------------------#
# In several cases below, we use the .SECONDARY target to prevent associated 
# dependencies from being automatically removed by make.  This happens when
# a sub-rule fires during the course of a dependency chain-of-events to build
# some high-level target.  Preserving secondary targets minimizes unnecessary
# rebuild activity.
#---------------------------------------------------------------------------#

ifeq "$(check_md5)" "yes"
#---------------------------------------------------------------------------#
# NB: Specify python.tgz as secondary so it doesn't get auto-deleted by the 
#     md5chk rule.  It's handy to have pristine source *.tgz hanging around 
#     and the download step can be relatively expensive.
#---------------------------------------------------------------------------#
.SECONDARY: $(externaldir)/$(python_pkg_tgz)
%.tgz.md5chk: expected_md5 = $($(patsubst %.tgz.md5chk,%.tgz,$(@F))_md5)
%.tgz.md5chk: expected_zd5 = $($(patsubst %.tgz.md5chk,%.tgz,$(@F))_zd5)
%.tgz.md5chk: srctgz = $(patsubst %.tgz.md5chk,%.tgz,$@)
%.tgz.md5chk: %.tgz
	@if [ -z "$(expected_md5)" -a -z "$(expected_zd5)" ];then
		echo "Expected md5 sum for $(srctgz) is unknown."
		echo "Please make this known to the makefile if you want md5 sum checking."
		exit 1
	fi
	actual_md5=$$(md5sum $(srctgz) | awk '{print $$1}')
	valid_md5_list="$(expected_md5) $(expected_zd5) end_of_list"
	for valid_md5 in $${valid_md5_list}
	do
		case $${valid_md5} in
			"end_of_list")
				echo "md5 check failed for $@"
				exit 1
				;;
			[0-9,a-f,A-F]*)
				if [ "$${actual_md5}" = "$${valid_md5}" ];then
					echo $${actual_md5} > $@
					break
				fi
				;;
			*)
				echo "unexpected md5 string: $${valid_md5}"
				;;
		esac
	done
endif

%.tgz.unpacked : srctgz = $(patsubst %.tgz.unpacked,%.tgz,$@)
ifeq "$(check_md5)" "yes"
.SECONDARY: $(externaldir)/$(python_pkg_tgz).md5chk
%.tgz.unpacked : %.tgz.md5chk
else
%.tgz.unpacked : %.tgz
endif
	$(call cmd,UNTGZ,$(srctgz),$(@D))
	$(call cmd,TOUCH,$@)

#---------------------------------------------------------------------------#
# Be careful to specify order-only dependency between configure script
# and the *.unpacked sentinel file otherwise we'll get nuisance untar's of
# the python tgz even when the archived is alread unpacked.
#
# Why?  File modification times internal to the package are generally very old
# relative to our sentinel file that indicates the archive has been unpacked.
# It's likely the *.unpacked file will have a more recent modtime than
# the aged configure script within the python source archive that "depends"
# upon being unpacked from the archive for it's existence.
#---------------------------------------------------------------------------#
.ONESHELL: $(python_configure)
.SECONDARY: $(externaldir)/$(python_pkg).tgz.unpacked
$(python_configure): | $(externaldir)/$(python_pkg).tgz.unpacked
	@if [ ! -f "$(@)" ];then
		echo Recreate ./configure by unpacking tgz again.
		if [ -f "$(externaldir)/$(python_pkg).tgz.unpacked" ]; then
			$(call cmd_noat,RM,$(externaldir)/$(python_pkg).tgz.unpacked)
		fi
		if ! $(call cmd_noat,BUILD,$@,.,$(externaldir)/$(python_pkg).tgz.unpacked,) ;then
			exit 1
		fi
	fi

# Preserve configure-created, upstream Makefile during build process 
# so it is available later for use in install targets.
.SECONDARY: $(externaldir)/$(python_pkg)/Makefile
%/Makefile : configure_opts = $($(notdir $(@D))_configure_opts)
%/Makefile : %/configure
ifdef SHARED_LIBPYTHON
	@cd $(@D) ;\
	export LDFLAGS='$(python_LDFLAGS)' ;\
	export CFLAGS='$(python_CFLAGS)'   ;\
	$(call cmd_noat,CFGBLD,$(@D),$(configure_opts))
else
	@cd $(@D) ;\
	export CFLAGS='$(python_CFLAGS)' ;\
	$(call cmd_noat,CFGBLD,$(@D),$(configure_opts))
endif

# Force a reconfigure of the python source, by triggering
# the rule that causes python's Makefile to be created.
.PHONY: configure
.ONESHELL: configure
configure: 
	@if [ -f "$(python_makefile)" ];then
		$(call cmd_noat,RM,$(python_makefile))
	fi
	if ! $(call cmd_noat,BUILD,$@,.,$(python_makfile),) ;then
		exit 1
	fi

.PHONY: python
python: $(built_python)

$(built_python): | $(CHECKED_ENV)

# Build python from source.  
# (Makefile must already be configured into existence.)
%/$(python_pkg)/python: %/$(python_pkg)/Makefile
	$(call cmd,BUILD,$@,$(<D),all,)

# Create the install directory.  If the DESTDIR variable
# is null, you may need rootly powers.
#
# e.g., $(DESTDIR)/opt/zenoss
#
$(_DESTDIR)$(prefix):
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

#---------------------------------------------------------------------------#
# Install the complete python package under $(DESTDIR)$(prefix).
#
# e.g., $(DESTDIR)/opt/zenoss/{bin,lib,include}
#
# $(prefix) is set to a default value in zenmagic.mk.
#
# $(DESTDIR) is a shell variable, often null, but may be used for staged
# installs to a temporary location.  It's generally used during packaging
# builds but also leveraged in our sandbox-relative install targets 
# (e.g., export, installhere).
#
# Use the upstream's altinstall target for most of this, but
# overcome some weakness there with our manifests to
# ensure all files, links, and directories have desired ownership.
# Otherwise altinstall it will leave a subset of files and links 
# owned by root.
#
# NB: Some files in the python package have embedded spaces.  Manipulate the
#     internal field separator (IFS) during file reads to get the full
#     filename.
#---------------------------------------------------------------------------#
.PHONY: install
install: uppercase_target = $(shell echo $@ | tr '[:lower:]' '[:upper:]')
install: $(files_manifest) $(links_manifest) $(dirs_manifest)
install: | $(_DESTDIR)$(prefix)
	@if [ ! -f "$(built_python)" ]; then \
                echo "Unable to install $(program).  Missing $(built_python)." ;\
                echo $(LINE) ;\
                echo "Run 'make build' first" ;\
                echo ;\
                exit 1 ;\
        fi
	@if ($(call cmd_noat,MAKE_ALTINST,$(uppercase_target),$(dir $(built_python)),altinstall,DESTDIR=$(_DESTDIR) INSTALL="$(INSTALL) -c -o $(INST_OWNER) -g $(INST_GROUP)",$(_DESTDIR)$(bindir)/$(program))) ;then \
		cd $(_DESTDIR)$(bindir)
		if [ -f python$(python_version_maj_min) ] ;then \
			if [ ! -L python ]; then \
				if ! ($(call cmd_noat,SYMLINK,python$(python_version_maj_min),python)) ; then \
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
		echo "Error installing using python's makefile." ;\
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
installhere: uppercase_target = $(shell echo $@ | tr '[:lower:]' '[:upper:]')
installhere: 
	@if [ ! -f "$(built_python)" ]; then \
                echo "Unable to install $(program).  Missing $(built_python)." ;\
                echo $(LINE) ;\
                echo "Run 'make build' first" ;\
                echo ;\
                exit 1 ;\
        fi
	@if ($(call cmd_noat,MAKE_ALTINST,$(uppercase_target),$(dir $(built_python)),altinstall,DESTDIR=$(abspath $(_DESTDIR)) INSTALL="$(INSTALL) -c -o $(INST_OWNER) -g $(INST_GROUP)",$(_DESTDIR)$(bindir)/$(program))) ;then \
		cd $(abspath $(_DESTDIR)$(bindir)) ;\
		if [ -f python$(python_version_maj_min) ] ;then \
			if [ ! -L python ]; then \
				if ! ($(call cmd_noat,SYMLINK,python$(python_version_maj_min),python)) ; then \
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
		echo "Error installing using python's makefile." ;\
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

$(exportto): uppercase_target = $(shell echo $@ | tr '[:lower:]' '[:upper:]')
$(exportto): 
	@if [ ! -f "$(built_python)" ]; then \
                echo "Unable to export $(program).  Missing $(built_python)." ;\
                echo $(LINE) ;\
                echo "Run 'make build' first" ;\
                echo ;\
                exit 1 ;\
        fi
	@if ($(call cmd_noat,MAKE_ALTINST,$(uppercase_target),$(dir $(built_python)),altinstall,DESTDIR=$(abspath $(exportdir)),$(exportdir))) ;then \
		cd $(abspath $(exportdir)/$(bindir))
		if [ -f python$(python_version_maj_min) ] ;then \
			if [ ! -L python ]; then \
				if ! ($(call cmd_noat,SYMLINK,python$(python_version_maj_min),python)) ; then \
					echo "Unable to create python symlink." ;\
					exit 1 ;\                                       
				fi ;\
			fi ;\
		else \
			echo "Missing $(exportdir)/$(bindir)/python$(python_version_maj_min)" ;\
			echo "Unable to create python symlink." ;\
			exit 1 ;\
		fi ;\
	else \
		echo "Error installing $(program) under $@." ;\
		exit 1 ;\
	fi

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
# Here we call into subshellcmd because the underlying manifest creation
# macros employ a subshell which is not tolerated well by the cmd macro.
# You'll get an error, otherwise, from echo because the subshell is not quoted.
#---------------------------------------------------------------------------#
%/files.manifest: $(heredir)$(bindir)/python | $(manifestdir)
	@($(call subshellcmd_noat,MK_F_MANIFEST,$(heredir),$(prefix),$@))

%/links.manifest: $(heredir)$(bindir)/python | $(manifestdir)
	@($(call subshellcmd_noat,MK_L_MANIFEST,$(heredir),$(prefix),$@))

%/dirs.manifest: $(heredir)$(bindir)/python | $(manifestdir)
	@($(call subshellcmd_noat,MK_D_MANIFEST,$(heredir),$(prefix),$(_DESTDIR)$(prefix),$@))
	$(call cmd,CHOWN,-R,$(INST_OWNER),$(INST_GROUP),$(manifestdir))

.PHONY: manifests
manifests: $(files_manifest) $(links_manifest) $(dirs_manifest)


#---------------------------------------------------------------------------#
# Manifest-based uninstall.
#---------------------------------------------------------------------------#
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
				echo "Please run: 'make manifests uninstall'"
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
											exit 1 
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
control_variables += dnstream_src_url
control_variables += exportdir 
control_variables += exportto 
control_variables += INST_GROUP 
control_variables += INST_OWNER 
control_variables += NEAREST_ZENMAGIC_MK 
control_variables += python_pkg_tgz
control_variables += python_version 
control_variables += prefer_dnstream 
control_variables += prefix 
control_variables += SHARED_LIBPYTHON 
control_variables += upstream_src_url 
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

#=============================================================================
# TODO:
#
# At configure time, search for the *.pc (pkg-config) files associated
# with these devel packages:
#
#       bzip2-devel    
#       openssl-devel 
#       ncurses-devel 
#       readline-devel 
#       tk-devel
#       sqlite-devel 
#       zlib-devel
#
# lest you get chatter at the end of the python build about inability to
# build various modules:
#
# Python build finished, but the necessary bits to build these modules were not found:
# _bsddb             _tkinter           bsddb185        
# bz2                dbm                dl              
# gdbm               imageop            sunaudiodev     
#
# See: http://toomuchdata.com/2012/06/25/how-to-install-python-2-7-3-on-centos-6-2/
#=============================================================================
