#=============================================================================
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
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
#    export         # Export the java script minifier into a 
#                   # sandbox-relative area visible to other minifier-needy
#                   # components.
#---------------------------------------------------------------------------#

#============================================================================
# Build component configuration.
#
# Beware of trailing spaces.
# Don't let your editor turn tabs into spaces or vice versa.
#============================================================================
COMPONENT = jsminifier
MKFILE    = $(COMPONENT).mk

#---------------------------------------------------------------------------#
# Specify java script minifier.
#---------------------------------------------------------------------------#
jsminifier = sencha_jsbuilder # sencha_jsbuilder | google_closure

# Local server which may host the minifier archive.
#
# If the archive is not found here, we'll end up searching for it on some
# upstream server on the net.
#
downstream_pkg_url = http://zenpip.zendev.org/packages
prefer_downstream  = yes # express preference for downstream over upstream url

# Specify if the md5 sum of the minifier archive should be verified 
# before unpacking it.  Not a bad idea if it got pulled from the network.
#
check_md5 = yes

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
NEAREST_ZENMAGIC_MK := $(word 1,$(wildcard ./zenmagic.mk $(shell for slash in $$(echo $(abspath .) | sed -e "s|.*\(/obj/\)\(.*\)|\1\2|g" | sed -e "s|[^/]||g" -e "s|/|/ |g"); do string=$${string}../;echo $${string}zenmagic.mk; done | xargs echo)))

ifeq "$(NEAREST_ZENMAGIC_MK)" ""
    $(warning "Missing zenmagic.mk needed by the $(COMPONENT)-component makefile.")
    $(warning "Unable to find our file of build idioms in the current or parent directories.")
    $(error   "A fully populated src tree usually resolves that.")
else
    include $(NEAREST_ZENMAGIC_MK)
endif

#---------------------------------------------------------------------------#
# Sencha's JSBuilder2
#
# Legacy minifier we use in our 4.x builds.  Classic, known, dated, unsexy.
#
# It uses a json-structured *.jsb2 file to define which *.js files to 
# aggregate into a single minified file (e.g., zenoss-compiled.js)
#
# Supposedly Sencha has an updated minifier.  We should look into using that
# or consider some of the more mainstream minifiers from yui or google.
#---------------------------------------------------------------------------#
sencha_jsbuilder_name         = JSBuilder2
sencha_jsbuilder_jar          = JSBuilder2.jar
sencha_jsbuilder_upstream_url = http://dev.sencha.com/deploy
sencha_jsbuilder_version      = 2
_sencha_jsbuilder_version    := $(strip $(sencha_jsbuilder_version))
sencha_jsbuilder_archive     := $(sencha_jsbuilder_name).zip
sencha_jsbuilder_rsync_FILTER = -f "- JSB2FileFormat.txt"
sencha_jsbuilder_rsync_OPTS   = $(sencha_jsbuilder_rsync_FILTER)
ifeq "$(check_md5)" "yes"
JSBuilder2.zip_md5            = bb07827ee0af146586dcdcf9dc4e1a1c
endif
#---------------------------------------------------------------------------#

#---------------------------------------------------------------------------#
# Google's Closure Compiler
# 
# New kid on the block. Smart, good-looking, full of promise. 
#
# Need to figure out the closure-equivalent of zenoss.jsb2 to drive this
# thing.
#---------------------------------------------------------------------------#
google_closure_name          = closure-compiler
google_closure_jar           = compiler.jar
google_closure_upstream_url  = http://dl.google.com/$(google_closure_name)
google_closure_version       = 20140110 # 20140110 | latest
_google_closure_version     := $(strip $(google_closure_version))
google_closure_archive       = compiler-$(_google_closure_version).tar.gz
ifeq "$(check_md5)" "yes"
compiler-20140110.tar.gz_md5 = 11cda035deb4b753bef17343aecc9e11  
endif
google_closure_rsync_FILTER  =
google_closure_rsync_OPTS    = $(google_closure_rsync_FILTER)
# Optimization level
# e.g., WHITESPACE_ONLY | SIMPLE_OPTIMIZATIONS | ADVANCED_OPTIMIZATIONS
google_closure_optimization  = --compilation_level SIMPLE_OPTIMIZATIONS 
                             # --compilation_level SIMPLE_OPTIMIZATIONS 
                             # --compilation_level WHITESPACE_ONLY
                             # --compilation_level ADVANCED_OPTIMIZATIONS
google_closure_formatting    = # --formatting PRETTY_PRINT
_google_closure_formatting   = $(strip $(google_closure_formatting))
#---------------------------------------------------------------------------#

# Specify where to locate the minifier archive.
#
# (You may also stage an archive local to your sandbox 
# and precedence will be given to that over the remote minifier archive.)
#
_jsminifier          = $(strip $(jsminifier))
_prefer_downstream   = $(strip $(prefer_downstream))
pkg_local_path      := ./$($(_jsminifier)_archive)
upstream_pkg_url    := $($(_jsminifier)_upstream_url)

# Attributes associated with the java script minifier we're staging.
jsminifier_rsync_OPTS               := $($(_jsminifier)_rsync_OPTS)
jsminifier_pkg                      := $(_jsminifier)-$(_$(_jsminifier)_version)
jsminifier_archive                  := $($(_jsminifier)_archive)
jsminifier_jar                      := $($(_jsminifier)_jar)
jsminifier_jar_unpacked              = $(externaldir)/$(jsminifier_pkg)/$(jsminifier_jar)
jsminifier_unpack_dir                = $(externaldir)/$(jsminifier_pkg)
jsminifier_unpacked_sentinal         = $(externaldir)/$(jsminifier_archive).unpacked
jsminifier_archive_downloaded        = $(externaldir)/$(jsminifier_archive)
jsminifier_jar_exported              = $(exportdir)/$(jsminifier_jar)
$(jsminifier_archive)_local_path     = ./$(jsminifier_archive)
$(jsminifier_archive)_downstream_url = $(downstream_pkg_url)/$(jsminifier_archive)
$(jsminifier_archive)_upstream_url   = $(upstream_pkg_url)/$(jsminifier_archive)

#
# Designate where to install the minifier.
#
# This follows the spirit of the FHS where non-arch specific files
# live under 'share'.  This is a reasonable assumption since minifiers
# are typically implemented as portable jar files.
#
jsminifier_jar_inst_dir  = share/java/$(jsminifier_pkg)
jsminifier_jar_installed = $(prefix)/$(jsminifier_jar_inst_dir)/$(jsminifier_jar)


#---------------------------------------------------------------------------#
# Variables for this makefile
#---------------------------------------------------------------------------#
bldtop = build

# The javascript minifier is an external dependency which we currently fold 
# into our build and packaging.  We package it so patches made to our
# javascript in the wild can be minified/compiled there as well.
#
# Underscore that external dependency relationship in our build-time 
# directory structure as a low-tech means for auditing same.  
#
# Specify the directory where we download the minifier archive 
# zip or tar.gz.
externaldir = $(bldtop)/external

#
# One day, this build should have a separate tools directory to aggregate
# tools not commonly available from the distro at the versions we require
# (e.g., protoc, jsminifier, lua-jit).  It would sit parallel to the checked 
# out code and could be hosted or bootstrapped by building from src/tools.
#
# tools/<arch>/<name>-<version>/<tool>
#
# src/core/{bin,Products}
#  |
#  +-/metric-consumer
#  |
#  +-/protocols
#  |
#  +-/(..)
#  |
#  +-/tools/{protoc.mk,lua-jit.mk,jsminifier.mk,python.mk,..}
#
# Until then, use the export directory to host the built minifier.
#
#    e.g.,  ./build/export/sencha_jsbuilder-2
#
# Conventionally, the export tree is where you place intermediate build
# results needed by subsequent phases of the build.
#
# exportdir = $(toolsdir)/$(jsminifier_pkg)
exportdir  = $(bldtop)/export/$(jsminifier_pkg)

#
# Allow for surgical installs and uninstalls of the minifier through
# auto-generated manifests.
#
# Specify the directory where the minifier manifests reside.
manifesttop    = $(heredir)/manifests
manifestdir    = $(manifesttop)/$(jsminifier_pkg)
files_manifest = $(abspath $(manifestdir)/files.manifest)
links_manifest = $(abspath $(manifestdir)/links.manifest)
dirs_manifest  = $(abspath $(manifestdir)/dirs.manifest)

# Convenience macros for key files we build or reference.
program           = $(jsminifier_jar)
built_jsminifier := $(jsminifier_jar_unpacked)

#============================================================================
# Subset of standard build targets our makefiles should implement.  
#
# See: http://www.gnu.org/prep/standards/html_node/Standard-Targets.html#Standard-Targets
#============================================================================

#---------------------------------------------------------------------------#
# Build Targets
#---------------------------------------------------------------------------#
.PHONY: all build jsminifier jar
all build: jsminifier

.PHONY: jsminifier
jsminifier jar: $(jsminifier_jar_unpacked)

$(externaldir) $(manifestdir) $(jsminifier_unpack_dir) $(exportdir):
	$(call cmd,MKDIR,$@)
	$(call cmd,CHOWN,,$(INST_OWNER),$(INST_GROUP),$@)

#---------------------------------------------------------------------------#
# Download the java script minifier archive.
#
# This usually amounts to a jar file wrappered in a *.zip or *.tar.gz.
# Look for it on a local 'downstream' server or get it from the upstream.
#
# Stage it here:
#
#    e.g., build/external/<jsminifier>.zip
#          build/external/<jsminifier>.tar.gz
#
# where it can then be unpacked by another rule.
#---------------------------------------------------------------------------#
.PHONY: download
download: $(jsminifier_archive_downloaded)

$(externaldir)/%.tar.gz : local_path     = $($(@F)_local_path)
$(externaldir)/%.tar.gz : upstream_url   = $($(@F)_upstream_url)
$(externaldir)/%.tar.gz : downstream_url = $($(@F)_downstream_url)
$(externaldir)/%.zip    : local_path     = $($(@F)_local_path)
$(externaldir)/%.zip    : upstream_url   = $($(@F)_upstream_url)
$(externaldir)/%.zip    : downstream_url = $($(@F)_downstream_url)
ifeq "$(_prefer_downstream)" "yes"
$(externaldir)/%.tar.gz : download_url_list = $($(@F)_downstream_url) $($(@F)_upstream_url)
$(externaldir)/%.zip    : download_url_list = $($(@F)_downstream_url) $($(@F)_upstream_url)
else
$(externaldir)/%.tar.gz : download_url_list = $($(@F)_upstream_url) $($(@F)_downstream_url)
$(externaldir)/%.zip    : download_url_list = $($(@F)_upstream_url) $($(@F)_downstream_url)
endif
#---------------------------------------------------------------------------#
$(externaldir)/%.tar.gz $(externaldir)/%.zip: | $(externaldir) $(jsminifier_unpack_dir)
	@if [ -f "$(local_path)" ];then \
		$(call cmd_noat,CP,$(local_path),$@) ;\
		rc=$$? ;\
		if [ $${rc} -ne 0 ];then \
			exit $${rc} ;\
		fi ;\
	else \
		for archive_url in $(download_url_list) ;\
		do \
			($(call cmd_noat,CURL,$@,$${archive_url})) ;\
			rc=$$? ;\
			if [ $${rc} -eq 0 ];then \
				break ;\
			fi ;\
		done ;\
	fi ;\
	if [ ! -f "$@" ];then \
		echo "Unable to stage $@" ;\
		exit 1 ;\
	fi

ifeq "$(check_md5)" "yes"
#---------------------------------------------------------------------------#
# Verify the md5 sum of the downloaded java script archive matches the 
# expected value.
#---------------------------------------------------------------------------#
# NB: Designate the downloaded java script archive as secondary so it 
#     doesn't get auto-deleted by the md5chk rule.  It's handy to have have 
#     the archive hanging around and the download step can be relatively
#     expensive.
#---------------------------------------------------------------------------#
.SECONDARY: $(jsminifier_archive_downloaded)
%.md5chk: expected_md5 = $($(patsubst %.md5chk,%,$(@F))_md5)
%.md5chk: expected_zd5 = $($(patsubst %.md5chk,%,$(@F))_zd5)
%.md5chk: archive      = $(patsubst %.md5chk,%,$@)
%.md5chk: %
	@if [ -z "$(expected_md5)" -a -z "$(expected_zd5)" ];then \
		echo "Expected md5 sum for $(archive) is unknown." ;\
		echo "Please make this known to the makefile if you want md5 sum checking." ;\
		exit 1 ;\
	fi ;\
	actual_md5=$$(md5sum $(archive) | awk '{print $$1}') ;\
	valid_md5_list="$(expected_md5) $(expected_zd5) end_of_list" ;\
	for valid_md5 in $${valid_md5_list} ;\
	do \
		case $${valid_md5} in \
			"end_of_list") \
				echo "md5 check failed for $@" ;\
				exit 1 ;\
				;; \
			[0-9,a-f,A-F]*) \
				if [ "$${actual_md5}" = "$${valid_md5}" ];then \
					echo $${actual_md5} > $@ ;\
					break ;\
				fi ;\
				;; \
			*) \
				echo "unexpected md5 string: $${valid_md5}" ;\
				;; \
		esac ;\
	done
endif

#---------------------------------------------------------------------------#
# Make:
#    build/external/sencha_jsbuilder-2/JSBuilder2.jar
#
# dependent upon:
#    build/external/JSBuilder2.zip.unpacked
#
# to trigger the jar to be unpacked.
#---------------------------------------------------------------------------#
$(jsminifier_jar_unpacked): | $(jsminifier_unpacked_sentinal) $(jsminifier_unpack_dir)

#---------------------------------------------------------------------------#
# Unpack the java script archive (possibly after having passed an md5 sum
# check).  Handle both *.tar.gz and *.zip files.
#---------------------------------------------------------------------------#
%.tar.gz.unpacked : archive_tar_gz  = $(patsubst %.tar.gz.unpacked,%.tar.gz,$@)
%.tar.gz.unpacked : unpack_into_dir = $(jsminifier_unpack_dir)
ifeq "$(check_md5)" "yes"
.SECONDARY: $(externaldir)/$(jsminifier_archive).md5chk
%.tar.gz.unpacked : %.tar.gz.md5chk
else
%.tar.gz.unpacked : %.tar.gz
endif
	$(call cmd,UNTGZ,$(archive_tar_gz),$(unpack_into_dir))
	$(call cmd,TOUCH,$@)

%.zip.unpacked : archive_zip     = $(patsubst %.zip.unpacked,%.zip,$@)
%.zip.unpacked : unpack_into_dir = $(jsminifier_unpack_dir)
ifeq "$(check_md5)" "yes"
.SECONDARY: $(externaldir)/$(jsminifier_archive).md5chk
%.zip.unpacked : %.zip.md5chk
else
%.zip.unpacked : %.zip
endif
	$(call cmd,UNZIP,$(archive_zip),$(unpack_into_dir))
	$(call cmd,TOUCH,$@)

#---------------------------------------------------------------------------#
# Export the minifier to an area under the build tree where 
# subscribing makefiles can find and invoke it (as opposed to installing
# it to /opt/zenoss/bin like we did in the bad old days).  This
# is key for creating separate build and install targets.
#
# Examples:
#
#    ./build/export/google_closure-20140110/compiler.jar
#    ./build/export/sencha_jsbuilder-2/JSBuilder2.jar
#---------------------------------------------------------------------------#
.PHONY: export
export: $(jsminifier_jar_exported)

$(jsminifier_jar_exported): $(built_jsminifier) | $(exportdir)
	@if [ ! -f "$(built_jsminifier)" ]; then \
		echo "Unable to export $(program).  Missing $(built_jsminifier)." ;\
		echo $(LINE) ;\
		echo "Run 'make -f ${MKFILE} build' first" ;\
		echo ;\
		exit 1 ;\
	else \
		$(call cmd_noat,RSYNC,$(dflt_rsync_OPTS) $(jsminifier_rsync_OPTS),$(dir $(built_jsminifier)),$(abspath $(@D))) ;\
	fi

#---------------------------------------------------------------------------#
# Create the install directory.  If the DESTDIR variable
# is null, you may need rootly powers.
#
# e.g., $(DESTDIR)/opt/zenoss
#---------------------------------------------------------------------------#
$(_DESTDIR)$(prefix) $(_DESTDIR)$(prefix)/$(jsminifier_jar_inst_dir):
	@($(call cmd_noat,MKDIR,$@)) ;\
	rc=$$? ;\
	if [ $${rc} -ne 0 ] ; then \
		echo $(LINE) ;\
		echo "Maybe you intended 'sudo make -f $(MKFILE) install' or 'make -f $(MKFILE) installhere' instead?" ;\
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
# Install the javascript minifier files under:
#
# e.g., $(DESTDIR)/opt/zenoss/share/java
#
# $(prefix) is set to a default value in zenmagic.mk.
#
# $(DESTDIR) is a shell variable, often null, but may be used for staged
# installs to a temporary location.  It's generally used during packaging
# builds but also leveraged in our sandbox-relative install targets 
# (e.g., export, installhere).
#
# NB: The IFS (internal field separator) idiom adds rigor if file names in a 
#     package have embedded spaces.  Not so much of an issue for the minifier, 
#     but this code was borrowed from the python makefile which required this 
#     fu so seems a shame to delete it.
#---------------------------------------------------------------------------#
.PHONY: install
install: install_dir = $(_DESTDIR)$(prefix)/$(jsminifier_jar_inst_dir)
install: $(files_manifest) $(links_manifest) $(dirs_manifest)
install: | $(_DESTDIR)$(prefix) $(_DESTDIR)$(prefix)/$(jsminifier_jar_inst_dir) $(BUILD_LOG)
	@if [ ! -f "$(built_jsminifier)" ]; then \
                echo "Unable to install $(program).  Missing $(built_jsminifier)." ;\
                echo $(LINE) ;\
                echo "Run 'make -f $(MKFILE) build' first" ;\
                echo ;\
                exit 1 ;\
        fi
	@if ($(call cmd_noat,RSYNC,$(dflt_rsync_OPTS) $(jsminifier_rsync_OPTS),$(dir $(built_jsminifier)),$(abspath $(install_dir)))) ;then \
		saveIFS=$(IFS) ;\
		IFS=$(echo -en "\n\b") ;\
		#while read installedFile ;\
		#do \
		#	_installedFile=$(_DESTDIR)$${installedFile} ;\
		#	if [ -f "$${_installedFile}" -o -L "$${_installedFile}" ];then \
		#		if ! ($(call cmd_noat,CHOWN,,$(INST_OWNER),$(INST_GROUP),$${_installedFile})) ;then \
		#			IFS=$${saveIFS} ;\
		#			exit 1 ;\
		#		fi ;\
		#	fi ;\
		#done < $(files_manifest) ;\
		#while read installedLink ;\
		#do \
		#	_installedLink=$(_DESTDIR)$${installedLink} ;\
		#	if [ -L "$${_installedLink}" ];then \
		#		if ! ($(call cmd_noat,CHOWN_LINK,$(INST_OWNER),$(INST_GROUP),$${_installedLink})) ;then \
		#			IFS=$${saveIFS} ;\
		#			exit 1 ;\
		#		fi ;\
		#	fi ;\
		#done < $(links_manifest)
		while read installedDir ;\
		do \
			_installedDir=$(_DESTDIR)$${installedDir} ;\
			if [ -d "$${_installedDir}" ];then \
				if ! ($(call cmd_noat,CHOWN,-R,$(INST_OWNER),$(INST_GROUP),$${_installedDir})) ;then \
					IFS=$${saveIFS} ;\
					exit 1 ;\
				fi ;\
			fi ;\
		done < $(dirs_manifest) ;\
		IFS=$${saveIFS} ;\
	else \
		echo "Error installing javascript minifier." ;\
		echo "Maybe you intended 'sudo make -f $(MKFILE) install' instead?" ;\
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
installhere: install_dir = $(_DESTDIR)$(prefix)/$(jsminifier_jar_inst_dir)
installhere: | $(BUILD_LOG)
	@if [ ! -f "$(built_jsminifier)" ]; then \
                echo "Unable to install $(program).  Missing $(built_jsminifier)." ;\
                echo $(LINE) ;\
                echo "Run 'make -f $(MKFILE) build' first" ;\
                echo ;\
                exit 1 ;\
        fi
	@if [ ! -d $(install_dir) ];then \
		$(call cmd_noat,MKDIR,$(install_dir)) ;\
	fi
	@if ! ($(call cmd_noat,RSYNC,$(dflt_rsync_OPTS) $(jsminifier_rsync_OPTS),$(dir $(built_jsminifier)),$(abspath $(install_dir)))) ;then \
		echo "Error installing javascript minifier." ;\
		exit 1 ;\
	fi
	$(call cmd,CHOWN,-R,$(INST_OWNER),$(INST_GROUP),$(abspath $(_DESTDIR)))

#---------------------------------------------------------------------------#
# Target used to trigger an install of the python package to a 
# sandbox-relative location:
#
#    ./here/opt/zenoss/share/java/<jsminifier>-<version>/<jsminifier>.jar
#
# before attempting a system level install:
#
#    /opt/zenoss/share/java/{...}
#---------------------------------------------------------------------------#
$(heredir)$(jsminifier_jar_installed):
	@$(MAKE) -f $(MKFILE) --no-print-directory installhere

#---------------------------------------------------------------------------#
# Targets to create manifests of all the associated files, links, and 
# directories that make up the installed python footprint.  These are used 
# to audit the installed package and to enable robust installs and 
# surgical uninstalls.
#
# Here we call into subshellcmd because the underlying manifest creation
# macros employ a subshell which is not tolerated well by the cmd macro.
# You'll get an error, otherwise, from echo because the subshell is not quoted.
#---------------------------------------------------------------------------#
%/files.manifest: $(heredir)$(jsminifier_jar_installed) | $(manifestdir)
	@($(call subshellcmd_noat,MK_F_MANIFEST,$(heredir),$(prefix),$@))

%/links.manifest: $(heredir)$(jsminifier_jar_installed) | $(manifestdir)
	@($(call subshellcmd_noat,MK_L_MANIFEST,$(heredir),$(prefix),$@))

%/dirs.manifest: $(heredir)$(jsminifier_jar_installed)  | $(manifestdir)
	@($(call subshellcmd_noat,MK_D_MANIFEST,$(heredir),$(prefix),$(_DESTDIR)$(prefix),$@))
	$(call cmd,CHOWN,-R,$(INST_OWNER),$(INST_GROUP),$(manifestdir))

.PHONY: manifests
manifests: $(files_manifest) $(links_manifest) $(dirs_manifest)


#---------------------------------------------------------------------------#
# Manifest-based uninstall.
#---------------------------------------------------------------------------#
.PHONY: uninstall
uninstall: | $(BUILD_LOG)
	@if [ ! -d "$(_DESTDIR)$(prefix)" ];then \
		echo ;\
		echo "$(_DESTDIR)$(prefix) not found.  Nothing to uninstall." ;\
		echo ;\
	else \
		if [ ! -w "$(_DESTDIR)$(prefix)" ];then \
			echo "Unable to remove files under $(_DESTDIR)$(prefix)" ;\
			echo "Maybe you intended 'sudo make -f $(MKFILE) uninstall' instead?" ;\
			echo ;\
		else \
			count=`ls -a1 $(_DESTDIR)$(prefix) 2>/dev/null | wc -l` ;\
			if ((count<=2));then \
				echo ;\
				echo "Nothing to uninstall under $(_DESTDIR)$(prefix)" ;\
				echo ;\
				exit 0 ;\
			fi ;\
			if [ ! -f "$(files_manifest)" -o ! -f "$(dirs_manifest)" ];then \
				echo ;\
				echo "Unable to uninstall without a manifest of installed files and directories." ;\
				echo ;\
				echo "Please run: 'make -f $(MKFILE) manifests uninstall'" ;\
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
							echo "Error removing $${_delFile}" ;\
							echo "Giving up on $@." ;\
							echo "Maybe you intended 'sudo make -f $(MKFILE) uninstall' instead?" ;\
							IFS=$${saveIFS} ;\
							exit $${rc}  ;\
						fi ;\
					fi ;\
				done < $(files_manifest) ;\
				while read delLink ;\
				do \
					_delLink=$(_DESTDIR)$${delLink} ;\
					if [ -L "$${_delLink}" -o -f "$${_delLink}" ];then \
						($(call cmd_noat,RMLINK,$${_delLink})) ;\
						rc=$$? ;\
						if [ $${rc} -ne 0 ];then \
							echo "Error removing $${_delLink}" ;\
							echo "Giving up on $@." ;\
							echo "Maybe you intended 'sudo make -f $(MKFILE) uninstall' instead?" ;\
							IFS=$${saveIFS} ;\
							exit $${rc} ;\
						fi ;\
					fi ;\
				done < $(links_manifest) ;\
				if find $(_DESTDIR)$(prefix) -type f -o -type l 2>/dev/null 1>&2 ;then \
					while read delDir ;\
					do \
						case $${delDir} in \
							/|/usr|/opt|/etc|/var|/bin|/sbin|/lib|/home|/root|/sys|/dev|/boot) \
								:;; \
							*) \
								_delDir=$(_DESTDIR)$${delDir} ;\
								if [ -d "$${_delDir}" ];then \
									count=`ls -a1 $${_delDir} 2>/dev/null | wc -l` ;\
									if ((count<=2));then \
										($(call cmd_noat,RMDIR,$${_delDir})) ;\
										rc=$$? ;\
										if [ $${rc} -ne 0 ];then \
											echo "Error removing $${_delDir}" ;\
											echo "   rm -rf $${_delDir}" ;\
											echo "Giving up on $@." ;\
											echo "Maybe you intended 'sudo make -f $(MKFILE) uninstall' instead?" ;\
											echo "Otherwise you will need to manually remove python from $(_DESTDIR)$(prefix)" ;\
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
				if [ -d "$(heredir)" ];then ;\
					if ! $(MAKE) -f $(MKFILE) --no-print-directory uninstallhere ;then \
						exit 1 ;\
					fi ;\
				fi ;\
			fi ;\
		fi ;\
	fi

.PHONY: help
help: 
	@echo
	@echo "Zenoss 5.x $(_COMPONENT) makefile"
	@echo
	@echo "Usage: make <target>"
	@echo "       make <target> V=1 # for verbose output"
	@echo
	@echo "where <target> is one or more of the following:"
	@echo $(LINE)
	@make -f $(MKFILE) -rpn | $(SED) -n -e '/^$$/ { n ; /^[^ ]*:/p ; }' | $(GREP) -v .PHONY| $(SORT) |\
	$(SED) -e "s|:.*||g" | $(EGREP) -v "Products|^\.|^$(blddir)\/|install|$(prefix)|^\/|^dflt_|clean|FORCE|^%|^here\/|^build\/|^Z|^Jobber|^Data|__init__.py|*.log" | $(PR) -t -w 80 -3
	@echo $(LINE)
	@make -f $(MKFILE) -rpn | $(SED) -n -e '/^$$/ { n ; /^[^ ]*:/p ; }' | $(GREP) -v .PHONY| $(SORT) |\
	$(SED) -e "s|:.*||g" | $(EGREP) -v "^\.|^$(blddir)\/|^$(prefix)\/|^\/|^dflt_|^%|^here\/|^build\/" | $(EGREP) clean | $(PR) -t -w 80 -3
	@echo $(LINE)
	@make -f $(MKFILE) -rpn | $(SED) -n -e '/^$$/ { n ; /^[^ ]*:/p ; }' | $(GREP) -v .PHONY| $(SORT) |\
	$(SED) -e "s|:.*||g" | $(EGREP) -v "^\.|^$(blddir)\/|^$(prefix)\/|^\/|^dflt_|^%|^here\/|^build\/|uninstall" | $(EGREP) install | $(PR) -t -w 80 -3
	@echo $(LINE)
	@make -f $(MKFILE) -rpn | $(SED) -n -e '/^$$/ { n ; /^[^ ]*:/p ; }' | $(GREP) -v .PHONY| $(SORT) |\
	$(SED) -e "s|:.*||g" | $(EGREP) -v "^\.|^$(blddir)\/|^$(prefix)\/|^\/|^dflt_|^%|^here\/|^build\/" | $(EGREP) uninstall | $(PR) -t -w 80 -3
	@echo $(LINE)
	@echo "Build results logged to $(BUILD_LOG)."
	@echo
	@echo Using common build idioms from $(NEAREST_ZENMAGIC_MK)
	@echo


# Variables of interest that we dump out if you run 'make settings'
# This will give you an idea of how the build will behave as currently
# configured.
control_variables  = bldtop 
control_variables += built_jsminifier
control_variables += DESTDIR
control_variables += downstream_pkg_url
control_variables += exportdir 
control_variables += externaldir
control_variables += google_closure_name
control_variables += google_closure_jar
control_variables += google_closure_upstream_url
control_variables += google_closure_version
control_variables += google_closure_archive
control_variables += google_closure_optimization
control_variables += INST_GROUP 
control_variables += INST_OWNER 
control_variables += jsminifier
control_variables += jsminifier_archive
control_variables += jsminifier_jar
control_variables += jsminifier_pkg
control_variables += jsminifier_archive_downloaded
control_variables += jsminifier_jar_inst_dir
control_variables += jsminifier_jar_installed
control_variables += NEAREST_ZENMAGIC_MK 
control_variables += pkg_local_path
control_variables += prefer_downstream 
control_variables += prefix 
control_variables += sencha_jsbuilder_name
control_variables += sencha_jsbuilder_jar
control_variables += sencha_jsbuilder_upstream_url
control_variables += sencha_jsbuilder_version
control_variables += sencha_jsbuilder_archive
control_variables += upstream_pkg_url 

.PHONY: settings
settings: 
	$(call show-vars,"Current makefile settings:",$(control_variables))

.PHONY: clean
clean:
	@if [ -d "$(bldtop)" ];then \
		if [ "$(abspath $(bldtop))" != "$(abspath $(pkgsrcdir))" ];then \
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
			$(call echol,"       pkgsrcdir $(abspath $(pkgsrcdir))") ;\
		fi ;\
	fi

.PHONY: mrclean
mrclean distclean: clean dflt_component_distclean
	@for deldir in $(heredir) ;\
	do \
		if [ -d "$${deldir}" ];then \
			$(call cmd_noat,RMDIR,$${deldir}) ;\
		fi ;\
	done
	@for delfile in $(BUILD_LOG) ;\
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
