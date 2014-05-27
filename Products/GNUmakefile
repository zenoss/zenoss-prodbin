#============================================================================
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
#============================================================================
# To do:  See bottom of this file.
#============================================================================

#============================================================================
# DONT PANIC: How to debug when things go wrong ...
#---------------------------------------------------------------------------#
# Generally, I get the most mileage out of this idiom:
#
#    echo "#!/bin/bash"       > debug.sh
#    make -n <buggy_target>  >> debug.sh
#    chmod +x debug.sh
#    ./debug.sh              # or possibly sh -x -v ./debug.sh
#
# The -n is a dry-run option that spills out the commands associated
# with building the target.
#
# You can then try running these commands directly via the debug script
# to sort out logic or syntax errors, backporting the fixes to the makefile.
#============================================================================

.DEFAULT_GOAL := help # build|clean|distclean|devinstall|install|help

#============================================================================
# Build component configuration.
#
# Beware of trailing spaces.
# Don't let your editor turn tabs into spaces or vice versa.
#============================================================================
COMPONENT = Products

# Specifying 'quick' uninstall removes the entire Products directory
# with one call to 'rm -rf Products'.  Otherwise a manifest-based
# uninstall occurs.  Manifest uninstalls may be useful if you want to
# preserve files that make it into $(prefix)/Products from other components
# or custom dev efforts.
#
QUICK_UNINSTALL   ?= yes

# Define build/install/uninstall targets for individual subdirs under 
# Products.
#
# e.g.,  make ZenModel
#        sudo make install-ZenModel
#        sudo make uninstall-ZenModel
#
# Useful if you're working in a specific area.
GRANULAR_DEV      ?= no

#
# Change ownership of links to 
#
#    $(INST_OWNER):$(INST_GROUP)
#
# Requires link manifest to be created.
#
CHOWN_LINKS       ?= no

# When python is invoked against a *.py file, it generates 
# byte code or optimized byte code files executed by the
# python virtual machine:
#
#    *.pyc
#    *.pyo
#
# Specify if you want these files to be removed with:
#
#    make mrclean     (for scrubbing src dir)
#    make uninstall   (for scrubbing inst dir)
#
MRCLEAN_PYC_PYO   ?= yes
UNINSTALL_PYC_PYO ?= yes

# This suppresses some gnumake chatter when it enters / leaves subdirectories.
gnumake_suppress_EnteringDir = --no-print-directory
gnumake_OPTS  := $(gnumake_suppress_EnteringDir)

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
NEAREST_ZENMAGIC_MK := $(word 1,$(wildcard ./zenmagic.mk $(shell for slash in $$(echo $(abspath .) | sed -e "s|.*\(/obj/\)\(.*\)|\1\2|g" | sed -e "s|[^/]||g" -e "s|/|/ |g"); do string=$${string}../;echo $${string}zenmagic.mk; done | xargs echo)))

ifeq "$(NEAREST_ZENMAGIC_MK)" ""
    $(warning "Missing zenmagic.mk needed by the $(COMPONENT)-component makefile.")
    $(warning "Unable to find our file of build idioms in the current or parent directories.")
    $(error   "A fully populated src tree usually resolves that.")
else
    include $(NEAREST_ZENMAGIC_MK)
endif

#---------------------------------------------------------------------------#
# Variables for this makefile
#---------------------------------------------------------------------------#
bldtop  = build
blddir  = $(bldtop)/$(_COMPONENT)
instdir = $(prefix)/$(_COMPONENT)
canary  = ZenModel/ZenModelBase.py
built_Products := $(blddir)/$(canary)
rsync_CHMOD    := --chmod=Du+wx,g+x,g-w,o-rwx,Fo-w

# Provide the ability to surgically install and uninstall the Products
# component.  Use manifests to keep track of the installed footprint.

manifesttop    = $(heredir)/manifests
manifestdir    = $(manifesttop)
files_manifest = $(abspath $(manifestdir)/files.manifest)
links_manifest = $(abspath $(manifestdir)/links.manifest)
dirs_manifest  = $(abspath $(manifestdir)/dirs.manifest)

# Build up a list of directories under Products.
Products := $(shell find . -maxdepth 1 -mindepth 1 -type d | egrep -v "$(heredir)|$(bldtop)" | sed -e "s|^\.\/||g")

# Prepend each entry in that list with the build directory so we get
# separation between the src dir and build dir.
built_Products_dirs := $(patsubst %,$(blddir)/%,$(Products))

ifeq "$(GRANULAR_DEV)" "yes"
# Define targets for each subdir in Products for granular installs.
# Useful if you're dev'ing on just a particular area of Products.
installjustthis     := $(patsubst %,install-%,$(Products))
uninstalljustthis   := $(patsubst %,uninstall-%,$(Products))
endif

#---------------------------------------------------------------------------#
# Javascript-related configuration for building stuff under:
#
#    Products/ZenUI3/browser/resources/js
#---------------------------------------------------------------------------#
#
# The current approach uses Sench'a jsbuilder2 minifier, though I've added
# some support for Google's closure compiler if you look at jsminifier.mk.
# Someone will need to figure out the closure-equivalent of zenoss.jsb2
# to drive the minification ... and then add the appropriate tar/dep rules
# here.
#
#---------------------------------------------------------------------------#
jsminifier = sencha_jsbuilder # sencha_jsbuilder | google_closure

#---------------------------------------------------------------------------#
# Approximately 100+ individaul zenoss javascript files are compressed into 
# a single 'minified' file as orchestrated by a json-structured jsb2 build
# file:
#
#                                       +--------------+
# ZenUI3/browser/zenoss.jsb2 ---------->|    sencha    |
# ZenUI3/browser/resources/js/*/*.js -->|   minifier   |-->zenoss-compiled.js
#                                       |--------------|
#                                       |JSBuilder2.jar|
#                                       +--------------+
#---------------------------------------------------------------------------#

# Specify the build-time location of the minifier.
# This drives how the minifier archive is unpacked and staged by 
# jsminifier.mk.
sencha_jsbuilder = build/export/sencha_jsbuilder-2/JSBuilder2.jar
_jsminifier      = $(strip $(jsminifier))

# Identify the sencha jsbuilder json build file.
zenoss_jsbasedir = ZenUI3/browser
zenoss_jsbmake   = $(zenoss_jsbasedir)/zenoss.jsb2

# Extract the output filename from the json build file so we can use it
# in a target/dependency relationship below.
#
#    e.g., zenoss-compiled.js
#
zenoss_compiled_js_name := $(shell grep file.*js $(zenoss_jsbmake) | awk '{print $$2}' | tr -d [\",])

# Extract the output directory from the json control file:
#
#    ZenUI3/browser/zenoss.jsb2
#    --------------------------
#    ...
#    "deployDir": "resources/js/deploy",
#                  ---------+---------
#                           |
#                           +--- jsb_deploy_dir
#
jsb_deploy_dir := $(shell grep deployDir.*: $(zenoss_jsbmake) | awk '{print $$2}' | tr -d [\",])

#
# e.g., ZenUI3/browser/resources/js/deploy
jsb_output_dir := $(zenoss_jsbasedir)/$(jsb_deploy_dir)

zenoss_compiled_js  = $(jsb_output_dir)/$(zenoss_compiled_js_name)
zenoss_blddir_js    = $(blddir)/$(jsb_output_dir)/$(zenoss_compiled_js_name)
zenoss_src_basedir  = $(zenoss_jsbasedir)/resources/js
zenoss_src_dirs    := $(shell find $(zenoss_src_basedir) -maxdepth 1 -mindepth 1 -type d | fgrep -v "$(jsb_output_dir)")
zenoss_src_js      := $(shell find $(zenoss_src_dirs) -type f -name \*.js)

#============================================================================
# Subset of standard build targets our makefiles should implement.  
#
# See: http://www.gnu.org/prep/standards/html_node/Standard-Targets.html#Standard-Targets
#============================================================================

#---------------------------------------------------------------------------#
# Build Targets
#---------------------------------------------------------------------------#
.PHONY: all build

# NB: We build js before Products because js is a bad pony and currently
#     builds /in/ the src tree (we'd need to tweak zenoss.jsb's deployDir to
#     make it behave otherwise).  Since Products is basically a glorified
#     copy, placing Products after js will cause him to sweep up the built
#     javascript from the src dir and dump it in the build tree.
#
all build: js Products

.PHONY: Products $(Products) 
Products: $(Products) $(blddir)/__init__.py

.PHONY: $(Products)
$(Products): rsync_OPTS = $(dflt_rsync_OPTS) $(rsync_CHMOD)
$(Products): | $(blddir)
	$(call cmd,RSYNC,$(rsync_OPTS),$@,$(blddir))

$(blddir)/__init__.py: | $(blddir)
$(blddir)/__init__.py: $(blddir)/% : %
	$(call cmd,RSYNC,$(dflt_rsync_OPTS),$<,$(@D))

$(blddir) $(built_Products_dirs) $(manifestdir) $(dir $(zenoss_blddir_js)):
	$(call cmd,MKDIR,$@)

.PHONY: js 
js: $(zenoss_blddir_js)

$(sencha_jsbuilder): exportdir = $(dir $(sencha_jsbuilder))
$(sencha_jsbuilder): | jsminifier.mk
	$(call cmd,EXPORT,$(_jsminifier),$(exportdir),jsminifier.mk,jsminifier=$(_jsminifier) exportdir=$(exportdir))

$(zenoss_compiled_js): $(zenoss_jsbmake) $(zenoss_src_js)| $(sencha_jsbuilder) $(blddir)/$(jsb_output_dir)
	$(call cmd,MINIFY_w_JSBUILDER,$(zenoss_src_basedir),$@,$(sencha_jsbuilder),$(zenoss_jsbmake),$(dir $(zenoss_jsbmake)))

$(zenoss_blddir_js): $(zenoss_compiled_js) | $(dir $(zenoss_blddir_js))
	$(call cmd,CP,$<,$@)

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
# Provide a dev-friendly install target that just symlinks the installed 
# Products directory back to your sandbox of checked out source:
#
#    /opt/zenoss/Products -> /home/me/sandbox/src/core/Products
#
# Useful for live-debug off a working directory and then committing changes
# back to version control.
#---------------------------------------------------------------------------#
.PHONY: devinstall
devinstall: | $(_DESTDIR)$(prefix) $(BUILD_LOG)
	@if [ -L "$(_DESTDIR)$(instdir)" ];then \
		instdirLink=`$(READLINK) -m $(_DESTDIR)$(instdir)` ;\
		if [ "$${instdirLink}" != "`pwd`" ];then \
			($(call cmd_noat,RM,$(_DESTDIR)$(instdir))) ;\
			rc=$$? ;\
			if [ $${rc} -ne 0 ];then \
				echo $(LINE) ;\
				echo ;\
				ls -l $(_DESTDIR)$(instdir) ;\
				echo ;\
				echo "Maybe you intended 'sudo make $@' instead?" ;\
				echo ;\
				exit 1 ;\
			fi ;\
		else \
			echo "Already devinstalled:" ;\
			echo $(LINE) ;\
			ls -l $(_DESTDIR)$(instdir) ;\
			echo ;\
			exit 0 ;\
		fi ;\
	fi ;\
	if [ -d "$(_DESTDIR)$(instdir)" ];then \
		echo $(LINE) ;\
		echo "Warning: I want to $@ for you:" ;\
		echo ;\
		echo "   $(_DESTDIR)$(instdir) -> `pwd`" ;\
		echo ;\
		echo "but first you need to move your existing $(_DESTDIR)$(instdir) directory" ;\
		echo "out of the way.  I don't want to kill something you may want." ;\
		echo ;\
		echo "If there is nothing of interest there, you could run:" ;\
		echo ;\
		echo "   sudo make uninstall" ;\
		echo ;\
		exit 1 ;\
	fi ;\
	if [ ! -w "$(_DESTDIR)$(prefix)" ];then \
		echo $(LINE) ;\
		echo "Error. You don't have permission to write files under $(_DESTDIR)$(prefix)." ;\
		echo "Maybe you intended 'sudo make $@' instead?" ;\
		echo ;\
		exit 1 ;\
	fi ;\
	($(call cmd_noat,SYMLINK,`pwd`,$(_DESTDIR)$(instdir))) ;\
	rc=$$? ;\
	if [ $${rc} -ne 0 ];then \
		echo $(LINE) ;\
		echo "Maybe you intended 'sudo make $@' instead?" ;\
		echo ;\
		exit 1 ;\
	fi ;\
	if ! $(call cmd_noat,CHOWN_LINK,$(INST_OWNER),$(INST_GROUP),$(_DESTDIR)$(instdir)) ;then \
		exit 0 ;\
	fi

#---------------------------------------------------------------------------#
# Install the complete Products component under $(DESTDIR)$(prefix) using
# manifests that specify associated directories, files, and links.
#
# e.g., $(DESTDIR)/opt/zenoss/Products
#
# $(prefix) is set to a default value in zenmagic.mk.
#
# $(DESTDIR) is a shell variable, often null, but may be used for staged
# installs to a temporary location.  It's generally used during packaging
# builds but also leveraged in our sandbox-relative install targets 
# (e.g., installhere).
#
# NB: If some files in the Products component have embedded spaces, manipulate
#     the internal field separator (IFS) during file reads to get the full
#     filename.
#---------------------------------------------------------------------------#
.PHONY: install
ifeq "$(CHOWN_LINKS)" "yes"
install: $(links_manifest)
endif
install: rsync_OPTS = $(dflt_rsync_OPTS) $(rsync_CHMOD)
install: | $(_DESTDIR)$(prefix) $(BUILD_LOG)
	@if [ ! -f "$(built_Products)" ]; then \
		echo "Unable to install $(_COMPONENT)." ;\
		echo $(LINE) ;\
		echo "Run 'make build' first" ;\
		echo ;\
		exit 1 ;\
	fi ;\
	if [ -L "$(_DESTDIR)$(instdir)" ];then \
		echo ;\
		echo "You're already devinstall'ed to a sandbox directory so this seems unnecessary." ;\
		echo "Bad things may happen, given my limited sophistication, if I do what you ask." ;\
		echo $(LINE) ;\
		ls -l $(_DESTDIR)$(instdir) ;\
		echo ;\
		echo "You could always run 'sudo make uninstall' first to remove your devinstall link." ;\
		echo ;\
		exit 0 ;\
	fi ;\
	if [ ! -w "$(_DESTDIR)$(prefix)" ];then \
		echo $(LINE) ;\
		echo "Error. You don't have permission to write files under $(_DESTDIR)$(prefix)." ;\
		echo "Maybe you intended 'sudo make $@' instead?" ;\
		echo ;\
		exit 1 ;\
	fi ;\
	($(call cmd_noat,RSYNC,$(rsync_OPTS),$(blddir),$(_DESTDIR)$(prefix))) ;\
	rc=$$? ;\
	if [ $${rc} -ne 0 ];then \
		echo $(LINE) ;\
		echo "Error installing $(_COMPONENT) under $(_DESTDIR)$(prefix)." ;\
		echo "Maybe you intended 'sudo make $@' instead?" ;\
		echo ;\
		exit 1 ;\
	fi ;\
	if ! ($(call cmd_noat,CHOWN,-R,$(INST_OWNER),$(INST_GROUP),$(_DESTDIR)$(instdir))) ;then \
		echo $(LINE) ;\
		echo "Error changing ownership under $(_DESTDIR)$(instdir)" ;\
		echo "Maybe you intended 'sudo make $@' instead?" ;\
		echo ;\
		exit 1 ;\
	fi ;\
	if [ "$(CHOWN_LINKS)" = "yes" ]; then \
		saveIFS=$(IFS) ;\
		IFS=$(echo -en "\n\b") ;\
		if [ -f "$(links_manifest)" ]; then \
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
		fi ;\
	fi

ifeq "$(GRANULAR_DEV)" "yes"
.PHONY: $(installjustthis)
$(installjustthis): this = $(patsubst install-%,%,$@)
$(installjustthis): rsync_OPTS = $(dflt_rsync_OPTS) $(rsync_CHMOD)
$(installjustthis): | $(_DESTDIR)$(prefix) $(BUILD_LOG)
	@if [ ! -d "$(blddir)/$(this)" ]; then \
                echo "Unable to install $(_COMPONENT)/$(this).  Missing $(blddir)/$(this)." ;\
                echo $(LINE) ;\
                echo "Run 'make $(this)' first" ;\
		echo ;\
		exit 1 ;\
	fi ;\
	if [ -L "$(_DESTDIR)$(instdir)" ];then \
		echo ;\
		echo "You're already devinstall'ed to a sandbox directory so this seems unnecessary." ;\
		echo "Bad things may happen, given my limited sophistication, if I do what you ask." ;\
		echo $(LINE) ;\
		ls -l $(_DESTDIR)$(instdir) ;\
		echo ;\
		echo "You could always run 'sudo make uninstall' first to remove your devinstall link" ;\
		echo "but that will essentially uninstall all of Products." ;\
		echo ;\
		exit 0 ;\
	fi ;\
	if [ -L "$(_DESTDIR)$(instdir)/$(this)" ];then \
		echo ;\
		echo "You're already devinstall'ed on $(this) to a sandbox directory so this seems unnecessary." ;\
		echo "Bad things may happen, given my limited sophistication, if I do what you ask." ;\
		echo $(LINE) ;\
		ls -l $(_DESTDIR)$(instdir)/$(this) ;\
		echo ;\
		echo "You could always run 'sudo make uninstall-$(this)' first to remove your devinstall link." ;\
		echo ;\
		exit 0 ;\
	fi ;\
	if [ ! -w "$(_DESTDIR)$(prefix)" ];then \
		echo $(LINE) ;\
		echo "Error. You don't have permission to write files under $(_DESTDIR)$(prefix)." ;\
		echo "Maybe you intended 'sudo make $@' instead?" ;\
		echo ;\
		exit 1 ;\
	fi ;\
	($(call cmd_noat,RSYNC,$(rsync_OPTS),$(blddir)/$(this),$(_DESTDIR)$(instdir))) ;\
	rc=$$? ;\
	if [ $${rc} -ne 0 ];then \
		echo $(LINE) ;\
		echo "Error installing $(_COMPONENT)/$(this) under $(_DESTDIR)$(instdir)/$(this)" ;\
		echo "Maybe you intended 'sudo make $@' instead?" ;\
		echo ;\
		exit 1 ;\
	fi ;\
	if ! ($(call cmd_noat,CHOWN,-R,$(INST_OWNER),$(INST_GROUP),$(_DESTDIR)$(instdir)/$(this))) ;then \
		echo $(LINE) ;\
		echo "Error changing ownership under $(_DESTDIR)$(instdir)/$(this)" ;\
		echo "Maybe you intended 'sudo make $@' instead?" ;\
		echo ;\
		exit 1 ;\
	fi
endif

#---------------------------------------------------------------------------#
# Attempt a sandbox-relative install.  If that fails, then we should probably
# fix that before attempting a 'sudo make install' onto the system.
#
# This is also our mechanism for creating manifests prior to a system-level 
# install.  Manifests give us traceability of files associated with a 
# component and surgical uninstall ability.
#---------------------------------------------------------------------------#
.PHONY: installhere
installhere: rsync_OPTS = $(dflt_rsync_OPTS) $(rsync_CHMOD)
installhere: 
	@if [ ! -f "$(built_Products)" ]; then \
                echo "Unable to install $(_COMPONENT)." ;\
                echo $(LINE) ;\
                echo "Run 'make build' first" ;\
                echo ;\
                exit 1 ;\
        fi
	@if [ ! -d "$(_DESTDIR)$(prefix)" ]; then \
		$(call cmd_noat,MKDIR,$(_DESTDIR)$(prefix)) ;\
	fi
	$(call cmd,RSYNC,$(rsync_OPTS),$(blddir),$(_DESTDIR)$(prefix))
	$(call cmd,CHOWN,-R,$(INST_OWNER),$(INST_GROUP),$(abspath $(_DESTDIR)))

$(heredir)$(instdir)/$(canary):
	@$(MAKE) $(gnumake_OPTS) installhere

#---------------------------------------------------------------------------#
# Targets to create manifests of all the associated files, links, and 
# directories that make up the installed Packages footprint.  These are used 
# to audit what comprises the installed package and to enable robust installs 
# and surgical uninstalls.
#
# Here we call into subshellcmd because the underlying manifest creation
# macros employ a subshell which is not tolerated well by the cmd macro.
# You'll get an error, otherwise, from echo because the subshell is not quoted.
#---------------------------------------------------------------------------#
%/files.manifest: $(heredir)$(instdir)/$(canary) | $(manifestdir) 
	@($(call subshellcmd_noat,MK_F_MANIFEST,$(heredir),$(prefix),$@))

%/links.manifest: $(heredir)$(instdir)/$(canary) | $(manifestdir)
	@($(call subshellcmd_noat,MK_L_MANIFEST,$(heredir),$(prefix),$@))

%/dirs.manifest: $(heredir)$(instdir)/$(canary) | $(manifestdir)
	@($(call subshellcmd_noat,MK_D_MANIFEST,$(heredir),$(prefix),$(_DESTDIR)$(prefix),$@))
	$(call cmd,CHOWN,-R,$(INST_OWNER),$(INST_GROUP),$(manifestdir))

.PHONY: manifests
manifests =  $(files_manifest) $(links_manifest) $(dirs_manifest)
manifests: $(manifests)

#---------------------------------------------------------------------------#
# Manifest-based uninstall.
#---------------------------------------------------------------------------#
.PHONY: uninstall
ifeq "$(QUICK_UNINSTALL)" "yes"
uninstall: | $(BUILD_LOG)
else
uninstall: | $(manifests) $(BUILD_LOG)
endif
	@if [ ! -d "$(_DESTDIR)$(prefix)" ];then \
		echo ;\
		echo "$(_DESTDIR)$(prefix) not found.  Nothing to uninstall." ;\
		echo ;\
	else \
		if [ ! -w "$(_DESTDIR)$(prefix)" ];then \
			echo $(LINE) ;\
			echo "Error. You don't have permission to remove files under $(_DESTDIR)$(prefix)." ;\
			echo "Maybe you intended 'sudo make $@' instead?" ;\
			echo ;\
			exit 1 ;\
		else \
			count=`ls -a1 $(_DESTDIR)$(prefix) 2>/dev/null | wc -l` ;\
			if ((count<=2));then \
				echo $(LINE) ;\
				echo "Nothing to uninstall under $(_DESTDIR)$(prefix)" ;\
				echo ;\
				exit 0 ;\
			fi ;\
			if [ "$(QUICK_UNINSTALL)" = "yes" ];then \
				($(call cmd_noat,RMDIR,$(_DESTDIR)$(instdir))) ;\
				rc=$$? ;\
				if [ $${rc} -ne 0 ] ; then \
					echo $(LINE) ;\
					echo "Error removing $(_DESTDIR)$(instdir)." ;\
					echo ;\
					exit $${rc} ;\
				fi ;\
			else \
				if [ ! -f "$(files_manifest)" -o ! -f "$(dirs_manifest)" ];then \
					echo $(LINE) ;\
					echo "Unable to uninstall without a manifest of installed files and directories." ;\
					echo ;\
					echo "Please run: 'make manifests uninstall'" ;\
					echo ;\
					exit 1 ;\
				else \
					saveIFS=$(IFS) ;\
					IFS=$(echo -en "\n\b") ;\
					while read delFile ;\
					do \
						_delFile=$(_DESTDIR)$${delFile} ;\
						if [ -f "$${_delFile}" -o -L "$${_delFile}" ];then \
							($(call cmd_noat,RM,$${_delFile})) ;\
							rc=$$? ;\
							if [ $${rc} -ne 0 ];then \
								echo $(LINE) ;\
								echo "Error removing $${_delFile}" ;\
								echo "Giving up on $@." ;\
								echo "Maybe you intended 'sudo make $@' instead?" ;\
								echo ;\
								IFS=$${saveIFS} ;\
								exit $${rc} ;\
							fi ;\
						fi ;\
					done < $(files_manifest) ;\
					while read delLink ;\
					do \
						_delLink=$(_DESTDIR)$${delLink} ;\
						if [ -L "$${_delLink}" -o -f "$${_delLink}" ];then \
							($(call cmd_noat,RM,$${_delLink})) ;\
							rc=$$? ;\
							if [ $${rc} -ne 0 ];then \
								echo $(LINE) ;\
								echo "Error removing $${_delLink}" ;\
								echo "Giving up on $@." ;\
								echo "Maybe you intended 'sudo make $@' instead?" ;\
								echo ;\
								IFS=$${saveIFS} ;\
								exit $${rc} ;\
							fi ;\
						fi ;\
					done < $(links_manifest) ;\
					if [ "$(UNINSTALL_PYC_PYO)" = "yes" ];then \
						($(call cmd_noat,RMGLOB,$(_DESTDIR)$(prefix),*.pyc)) ;\
						($(call cmd_noat,RMGLOB,$(_DESTDIR)$(prefix),*.pyo)) ;\
					fi ;\
					if find $(_DESTDIR)$(prefix) -type f -o -type l 2>/dev/null 1>&2 ;then \
						while read delDir ;\
						do \
							case $${delDir} in \
								/|/usr|/opt|/etc|/var|/bin|/sbin|/lib|/home|/root|/sys|/dev|/boot|/tmp)	 \
									:;; \
								*) \
									_delDir=$(_DESTDIR)$${delDir} ;\
									if [ -d "$${_delDir}" ];then \
										count=`ls -a1 $${_delDir} 2>/dev/null | wc -l` ;\
										if ((count<=2));then \
											($(call cmd_noat,RMDIR,$${_delDir})) ;\
											rc=$$? ;\
											if [ $${rc} -ne 0 ];then \
												echo $(LINE) ;\
												echo "Error removing $${_delDir}" ;\
												echo "   rm -rf $${_delDir}" ;\
												echo "Giving up on $@." ;\
												echo "Maybe you intended 'sudo make $@' instead?" ;\
												echo "Otherwise you will need to manually remove $(_COMPONENT) from $(_DESTDIR)$(prefix)" ;\
												echo ;\
												IFS=$${saveIFS} ;\
												exit 1  ;\
											fi ;\
										else \
											($(call cmd_noat,PSA,"RMDIR skipping","$${_delDir} Non-empty.")) ;\
										fi ;\
									fi ;\
									;; \
							esac ;\
						done < $(dirs_manifest) ;\
					fi ;\
					IFS=$${saveIFS} ;\
				fi ;\
			fi ;\
		fi ;\
	fi

ifeq "$(GRANULAR_DEV)" "yes"
.PHONY: $(uninstalljustthis)
$(uninstalljustthis): this = $(patsubst uninstall-%,%,$@)
$(uninstalljustthis): rsync_OPTS = $(dflt_rsync_OPTS) $(rsync_CHMOD)
$(uninstalljustthis): | $(_DESTDIR)$(prefix) $(BUILD_LOG)
	@if [ ! -d "$(_DESTDIR)$(prefix)" ];then \
		echo ;\
		echo "$(_DESTDIR)$(prefix) not found.  Nothing to uninstall." ;\
		echo ;\
	else \
		if [ ! -w "$(_DESTDIR)$(prefix)" ];then \
			echo $(LINE) ;\
			echo "Error. You don't have permission to remove files under $(_DESTDIR)$(prefix)." ;\
			echo "Maybe you intended 'sudo make $@' instead?" ;\
			echo ;\
			exit 1 ;\
		else \
			count=`ls -a1 $(_DESTDIR)$(prefix) 2>/dev/null | wc -l` ;\
			if ((count<=2));then \
				echo $(LINE) ;\
				echo "Nothing to uninstall under $(_DESTDIR)$(prefix)" ;\
				echo ;\
				exit 0 ;\
			fi ;\
			if [ -L "$(_DESTDIR)$(instdir)" ];then \
				echo ;\
				echo "You're already devinstall'ed to a sandbox directory so this seems unnecessary." ;\
				echo "Bad things may happen, given my limited sophistication, if I do what you ask." ;\
				echo "You could end up removing $(this) from your working directory. :-(" ;\
				echo $(LINE) ;\
				ls -l $(_DESTDIR)$(instdir) ;\
				echo ;\
				echo "You could always run 'sudo make uninstall' first to remove your devinstall link" ;\
				echo "but that will essentially uninstall all of Products." ;\
				echo ;\
				exit 0 ;\
			fi ;\
			($(call cmd_noat,RMDIR,$(_DESTDIR)$(instdir)/$(this))) ;\
			rc=$$? ;\
			if [ $${rc} -ne 0 ] ; then \
				echo $(LINE) ;\
				echo "Error removing $(_DESTDIR)$(instdir)/$(this)." ;\
				echo ;\
				exit $${rc} ;\
			fi ;\
		fi ;\
	fi
endif

.PHONY: help
help:
ifeq "$(GRANULAR_DEV)" "yes"
	@echo
	@echo "Zenoss 5.x $(_COMPONENT) makefile"
	@echo
	@echo "Usage: make <target>"
	@echo "       make <target> V=1 # for verbose output"
	@echo
	@echo "where <target> is one or more of the following:"
	@echo $(LINE)
	@make -rpn | $(SED) -n -e '/^$$/ { n ; /^[^ ]*:/p ; }' | $(GREP) -v .PHONY| $(SORT) |\
	$(SED) -e "s|:.*||g" | $(EGREP) -v "^\.|^$(blddir)\/|install|$(prefix)|^\/|^dflt_|clean|FORCE|^%|^here\/|^build\/|__init__.py" | $(PR) -t -w 80 -3
	@echo $(LINE)
	@make -rpn | $(SED) -n -e '/^$$/ { n ; /^[^ ]*:/p ; }' | $(GREP) -v .PHONY| $(SORT) |\
	$(SED) -e "s|:.*||g" | $(EGREP) -v "^\.|^$(blddir)\/|^$(prefix)\/|^\/|^dflt_|^%|^here\/|^build\/" | $(EGREP) clean | $(PR) -t -w 80 -3
	@echo $(LINE)
	@make -rpn | $(SED) -n -e '/^$$/ { n ; /^[^ ]*:/p ; }' | $(GREP) -v .PHONY| $(SORT) |\
	$(SED) -e "s|:.*||g" | $(EGREP) -v "^\.|^$(blddir)\/|^$(prefix)\/|^\/|^dflt_|^%|^here\/|^build\/|uninstall" | $(EGREP) install | $(PR) -t -w 80 -3
	@echo $(LINE)
	@make -rpn | $(SED) -n -e '/^$$/ { n ; /^[^ ]*:/p ; }' | $(GREP) -v .PHONY| $(SORT) |\
	$(SED) -e "s|:.*||g" | $(EGREP) -v "^\.|^$(blddir)\/|^$(prefix)\/|^\/|^dflt_|^%|^here\/|^build\/" | $(EGREP) uninstall | $(PR) -t -w 80 -3
	@echo $(LINE)
	@echo "Build results logged to $(BUILD_LOG)."
	@echo
else
	@echo
	@echo "Zenoss 5.x $(_COMPONENT) makefile"
	@echo
	@echo "Usage: make <target>"
	@echo "       make <target> V=1 # for verbose output"
	@echo
	@echo "where <target> is one or more of the following:"
	@echo $(LINE)
	@make -rpn | $(SED) -n -e '/^$$/ { n ; /^[^ ]*:/p ; }' | $(GREP) -v .PHONY| $(SORT) |\
	$(SED) -e "s|:.*||g" | $(EGREP) -v "^\.|^$(blddir)\/|install|$(prefix)|^\/|^dflt_|clean|FORCE|^%|^here\/|^build\/|^Z|^Jobber|^Data|__init__.py|*.log" | $(PR) -t -w 80 -3
	@echo $(LINE)
	@make -rpn | $(SED) -n -e '/^$$/ { n ; /^[^ ]*:/p ; }' | $(GREP) -v .PHONY| $(SORT) |\
	$(SED) -e "s|:.*||g" | $(EGREP) -v "^\.|^$(blddir)\/|^$(prefix)\/|^\/|^dflt_|^%|^here\/|^build\/" | $(EGREP) clean | $(PR) -t -w 80 -3
	@echo $(LINE)
	@make -rpn | $(SED) -n -e '/^$$/ { n ; /^[^ ]*:/p ; }' | $(GREP) -v .PHONY| $(SORT) |\
	$(SED) -e "s|:.*||g" | $(EGREP) -v "^\.|^$(blddir)\/|^$(prefix)\/|^\/|^dflt_|^%|^here\/|^build\/|uninstall" | $(EGREP) install | $(PR) -t -w 80 -3
	@echo $(LINE)
	@make -rpn | $(SED) -n -e '/^$$/ { n ; /^[^ ]*:/p ; }' | $(GREP) -v .PHONY| $(SORT) |\
	$(SED) -e "s|:.*||g" | $(EGREP) -v "^\.|^$(blddir)\/|^$(prefix)\/|^\/|^dflt_|^%|^here\/|^build\/" | $(EGREP) uninstall | $(PR) -t -w 80 -3
	@echo $(LINE)
	@echo "Build results logged to $(BUILD_LOG)."
	@echo
endif
	@echo Using common build idioms from $(NEAREST_ZENMAGIC_MK)
	@echo
ifneq "$(GRANULAR_DEV)" "yes"
	@echo "Try playing with make GRANULAR_DEV=yes"
	@echo
endif

# Variables of interest that we dump out if you run 'make settings'
# This will give you an idea of how the build will behave as currently
# configured.
control_variables  = bldtop
control_variables += blddir
control_variables += built_Products_dirs
control_variables += $(rsync_CHMOD)
control_variables += DESTDIR
control_variables += GRANULAR_DEV
control_variables += prefix
control_variables += Products
control_variables += QUICK_UNINSTALL

.PHONY: settings
settings:
	$(call show-vars,"Current makefile settings:",$(control_variables))

.PHONY: clean
clean:
	@if [ -d "$(bldtop)" ];then \
		if [ "$(abspath $(bldtop))" != "`pwd`" ];then \
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
			$(call echol,"       srcdir `pwd`") ;\
		fi ;\
	fi ;\
	if [ -d "$(jsb_output_dir)" ];then \
		($(call cmd_noat,RMDIR,$(jsb_output_dir))) ;\
		rc=$$? ;\
		if [ $${rc} -ne 0 ] ; then \
			echo $(LINE) ;\
			echo "Problem removing $(jsb_output_dir)." ;\
			echo ;\
			exit $${rc} ;\
		fi ;\
	fi

mrclean distclean: clean dflt_component_distclean
	@for deldir in $(heredir) ;\
	do \
		if [ -d "$${deldir}" ];then \
			$(call cmd_noat,RMDIR,$${deldir}) ;\
		fi ;\
	done ;\
	if [ "$(MRCLEAN_PYC_PYO)" = "yes" ];then \
		($(call cmd_noat,RMGLOB,.,*.pyc)) ;\
		($(call cmd_noat,RMGLOB,.,*.pyo)) ;\
	fi ;\
	for delfile in $(BUILD_LOG) jsminifier.log ;\
	do \
		if [ -f "$${delfile}" ];then \
			$(RM) $${delfile} ;\
		fi ;\
	done

.PHONY: uninstallhere
uninstallhere: | $(BUILD_LOG)
	@if [ -d "$(heredir)" ];then \
		$(call cmd_noat,RMDIR,$(heredir)) ;\
	fi

#============================================================================
# To do:
#============================================================================
# 1. Building Products/ZenModel/data/{*.xml, *.sql.gz}
#
# Dumping and exporting xml should be handled in a more automatic way in the 
# build.  This archive embodies the zodb model and is used to populate the 
# zodb during fresh installs.  On upgrades, the zodb is amended through 
# migrate scripts that mutate the database.  The point is, we want the zodb
# to end up at the same state whether we got there from a fresh install or
# and upgrade to the same target version as a fresh install.
#
# Currently we put responsibility upon the developer for keeping the 
# zodb.sql.gz in sync with migrate scripts that change the object model.
# Humans sometime fail to dump the xml and regen the *.gz file (or they
# may do it incorrectly for lack of tribal knowledge).
#
# Production of the fils under ZenModel/data should probably be
# handled by a separate jenkins job which spins up zenoss with uplevel
# zodb and dumps the xml and generates the *.xml and zodb.sql.gz.  
# This could then be integrated back into version control or hosted on
# a file server that is visible at build time as required by dev and 
# packaging builds.
#
# 2. Add audit support for 'trunk-level' migrate scripts in branch builds
#
# We want to avoid situations like: https://jira.zenoss.com/browse/ZEN-10259
# This could be handled as a make variable we turn on in our branched builds.
# The build would flag the presence of entries in the migrate scripts that
# look like:
#
# Products/ZenModel/migrate/eventFlapping.py
# ...
# version = Migrate.Version(4, 2, 70)
#
# See: https://github.com/Zenoss/4.2.5-RPS/commit/3bd3e4f318e112f167325b260c953ae1c927070b#diff-2
#
# 3. Building Products/ZenUI3/browser/resources/deploy/zenoss-compiled.js
#
# The sencha build of zenoss-compiled.js is happening in the src tree as
# opposed to the build tree.  This violates the notion of keeping the src tree 
# pristine and requires the clean target to know about this one-off exception.
#
# This could be fixed by changing the deployDir variable in zenoss.jsb2.
# The more generalized fix is to configure in the deployDir prior to 
# minifying so the component's build directory is exposed to the minifier.
#
# Having said that, this 'bad' behavior is happily exploited, though, 
# during devinstalls where we symlink /opt/zenoss/Products back to the src tree.
#============================================================================
