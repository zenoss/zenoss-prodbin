#============================================================================
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
#============================================================================
.DEFAULT_GOAL := help # all|build|clean|install|uninstall|help

#============================================================================
# Build component configuration.
#
# Beware of trailing spaces.
# Don't let your editor turn tabs into spaces or vice versa.
#============================================================================
COMPONENT = etc_conf
conf_CHECK_TOOLS   = $(CHMOD)
conf_CHECK_TOOLS  += $(CMP)
conf_CHECK_TOOLS  += $(DIFF)
conf_CHECK_TOOLS  += $(MV)

#---------------------------------------------------------------------------#
# Establish the replace / preserve policy for installed conf files
# (similar to RPM's config file handling where merge responsibility is
# placed back on the human instead of simply overwriting existing
# conf files).
#
# NB: This could be enhanced to provide some automatic merge ability 
#     (i.e., adding new key-value pairs with zenglobalconf fu).
#
# +---------+--------------+-----------------------------------------------+
# | replace | merge_assist |behavior                                       |
# +---------+--------------+-----------------------------------------------+
# |    no   |   no         |preserve installed conf file                   |
# +---------+--------------+-----------------------------------------------+
# |    no   |   yes        |preserve installed conf file                   |
# |         |              |install uplevel conf as <conf>.new w/merge nag |
# +---------+--------------+-----------------------------------------------+
# |   yes   |   no         |replace installed conf file with uplevel conf  |
# +---------+--------------+-----------------------------------------------+
# |   yes   |   yes        |move downlevel installed conf to <conf>.save   |
# |         |              |install uplevel conf                           |
# |         |              |nag to merge customizations from <conf>.save   |
# +---------+--------------+-----------------------------------------------+
#
#---------------------------------------------------------------------------#
replace      = yes # replace existing conf file if new conf file is different
merge_assist = yes # invoke *.conf.save / *.conf.new algorithm
show_diff    = yes # show courtesy diff if merge nag thrown
install_triggers_rebuild = no # dev convenience; violates canonical 
                              # separation of install and build targets.

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
bldtop               = $(abspath build)
blddir               = $(bldtop)/etc

conf_perms           = $(CONF_FILE_PERMS)

# All conf files.
conf_dirs            = cron.daily cron.weekly logrotate.d sudoers.d
conf_files          := $(patsubst ./%,%,$(shell find $(conf_dirs) -type f -name zenoss\* | egrep -v "\.mk$|makefile"))

# All conf files with *.in suffix.
confin_files         = $(filter %.in,$(conf_files))

# Conf files requiring no special build processing.
built_conf_files    := $(filter-out %.in,$(patsubst %,$(blddir)/%,$(conf_files)))
# Conf files built from *.in files.
built_confin_files   = $(patsubst %,$(blddir)/%,$(patsubst %.in,%,$(confin_files)))

# All installed conf files.
install_dir         := $(subst //,/,$(_DESTDIR)$(sysconfdir))
install_conf_files  := $(patsubst %,$(install_dir)/%,$(patsubst %.in,%,$(conf_files)))
install_dirs        := $(sort $(foreach install_conf_file,$(install_conf_files),$(dir $(install_conf_file))))

_replace             = $(strip $(replace))
_merge_assist        = $(strip $(merge_assist))
_show_diff           = $(strip $(show_diff))
_install_triggers_rebuild = $(strip $(install_triggers_rebuild))

#============================================================================
# Subset of standard build targets our makefiles should implement.  
#
# See: 
# http://www.gnu.org/prep/standards/html_node/Standard-Targets.html#Standard-Targets
#============================================================================
.PHONY: all
all: build

.PHONY: help
help: dflt_component_help
	@echo Using common build idioms from $(NEAREST_ZENMAGIC_MK)
	@echo

# Variables of interest that we dump out if you run 'make settings'
# This will give you an idea of how the build will behave as currently
# configured.
control_variables  = bldtop
control_variables += blddir
control_variables += install_dir
control_variables += install_dirs
control_variables += merge_assist
control_variables += replace
control_variables += show_diff
control_variables += conf_files
control_variables += confin_files
control_variables += built_confin_files
control_variables += built_conf_files
control_variables += install_conf_files
control_variables += install_triggers_rebuild

.PHONY: settings
settings: 
	$(call show-vars,"Current makefile settings:",$(control_variables))

$(bldtop) $(blddir):
	$(call cmd,MKDIR,$@)

.PHONY: clean
.ONESHELL: clean
clean: 
	@if [ -d "$(bldtop)" ];then
		$(call cmd_noat,RMDIR,$(bldtop))
	fi

.PHONY: mrclean
mrclean: clean dflt_component_mrclean

.PHONY: build
build: $(built_conf_files) $(built_confin_files)

$(built_conf_files): $(blddir)/% : % | $(CHECKED_ENV) $(blddir)
	@if [ ! -d "$(@D)" ];then \
		$(call cmd_noat,MKDIR,$(@D)) ;\
	fi
	$(call cmd,CP,$<,$@)

$(built_confin_files): $(blddir)/% : %.in | $(blddir)
	@if [ ! -d "$(@D)" ];then \
		$(call cmd_noat,MKDIR,$(@D)) ;\
	fi
	$(call cmd,SEDTEE,"s|@prefix@|$(prefix)|g",$<,$@)

# If we're doing an actual install into the system /etc, then enforce root ownership,
# otherwise assume ownership is the same as the mortal performing the staged install.
ifeq "$(_DESTDIR)" ""
    INST_OWNER=root
    INST_GROUP=root
endif

.ONESHELL: $(install_dir) $(install_dirs)
$(install_dir) $(install_dirs):
	@($(call cmd_noat,INSTALLDIR,$@,775,$(INST_OWNER),$(INST_GROUP)))
	rc=$$?
	if [ $${rc} -ne 0 ]; then 
		$(call echol,"Error making $@.")
		$(call echol,$(LINE))
		$(call echol,"Maybe you intended 'sudo make install' instead?")
		exit $${rc}
	fi

.PHONY: install
install: $(install_conf_files)

# http://www.gnu.org/software/make/manual/make.html#Force-Targets
#
# If a rule has no prerequisites or recipe, and the target of the rule is a 
# nonexistent file, then make imagines this target to have been updated 
# whenever its rule is run. This implies that all targets depending on 
# this one will always have their recipe run. 
#
FORCE:

#---------------------------------------------------------------------------#
# Install *.conf files.  
#
# This rule is a bit involved because it detects scenarios where you may 
# have to merge new content into an already installed conf file.
#
# If you just want to blindly replace the installed conf file, set:
#
#    replace = yes
#
# or install thusly:
#
#    sudo make install replace=yes
#
# The rule is somewhat smart in that it detects if two files are the
# same and will avoid a nuisance install.
#---------------------------------------------------------------------------#
.ONESHELL: $(install_conf_files)
$(install_conf_files) : bldtarget = $(patsubst $(install_dir)%,$(blddir)%,$@)
ifeq "$(_install_triggers_rebuild)" "yes"
$(install_conf_files) : $(install_dir)/% : $(blddir)/% | $(install_dirs)
else
# NB: We need to make this rule always fire (via FORCE) otherwise local changes will
#     not refresh already installed files.
$(install_conf_files) : FORCE
$(install_conf_files) : | $(install_dirs)
endif
	@if [ ! -f "$(bldtarget)" ];then
		$(call echol, "Unable to install $@.  Missing $(bldtarget).")
		$(call echol, $(LINE))
		$(call echol, "Run 'make build' first")
		exit 1
	fi
	if [ -f "$@" -o -L "$@" ];then 
		if ! $(CMP) -s $@ $(bldtarget) ; then
ifeq "$(_replace)" "no"
    ifeq "$(_merge_assist)" "no"
			$(call echol,"Preserving: $@ (downlevel) [since replace = $(_replace)]")
    else
			$(call echol,"Preserving: $@ (downlevel) [since replace = $(_replace)]")
			($(call cmd_noat,INSTALL,$(bldtarget),$(@).new,$(conf_perms),$(INST_OWNER),$(INST_GROUP)))
			rc=$$?
			if [ $${rc} -ne 0 ]; then 
				$(call echol,"Error installing $@.")
				$(call echol,$(LINE))
				$(call echol,"Maybe you intended 'sudo make install' instead?")
				exit $${rc}
			fi
			$(call ECHOL,>>,"Merge from: $@.new (uplevel) as desired.")
        ifeq "$(_show_diff)" "yes"
			$(call echol,$(LINE))
            ifeq "$(ZEBUILD_VERBOSE)" "1"
			$(call echol,"$(DIFF) -Nurp $@ $@.new")
			$(DIFF) -Nurp $@ $@.new || $(TRUE)
            else
			($(call cmd_noat,DIFF,-Nurp,$@,$@.new))
			$(DIFF) -Nurp $@ $@.new || $(TRUE)
            endif
			$(call echol,$(LINE))
        endif
    endif
else
    ifeq "$(_merge_assist)" "no"
			$(call echol,"Overwriting: $@ [since replace = $(_replace)]")
			($(call cmd_noat,INSTALL,$(bldtarget),$@,$(conf_perms),$(INST_OWNER),$(INST_GROUP)))
			rc=$$?
			if [ $${rc} -ne 0 ]; then 
				$(call echol,"Error installing $@.")
				$(call echol,$(LINE))
				$(call echol,"Maybe you intended 'sudo make install' instead?")
				exit $${rc}
			fi
    else
			$(call echol,"Renaming:   $@ as $(@F).save [since merge_assist = $(_merge_assist)]")
			($(call cmd_noat,MV,$@,$@.save))
			rc=$$?
			if [ $${rc} -ne 0 ]; then 
				$(call echol,"Error renaming $@.")
				$(call echol,$(LINE))
				$(call echol,"Maybe you intended 'sudo make install' instead?")
				exit $${rc}
			fi
			$(call echol,"Installing: $@ (uplevel)")
			($(call cmd_noat,INSTALL,$(bldtarget),$@,$(conf_perms),$(INST_OWNER),$(INST_GROUP)))
			rc=$$?
			if [ $${rc} -ne 0 ]; then 
				$(call echol,"Error installing $@.")
				$(call echol,$(LINE))
				$(call echol,"Maybe you intended 'sudo make install' instead?")
				exit $${rc}
			fi
			$(call ECHOL,>>,"Merge from: $@.save (downlevel) as desired.")
        ifeq "$(_show_diff)" "yes"
			$(call echol,$(LINE))
            ifeq "$(ZEBUILD_VERBOSE)" "1"
			$(call echol,"$(DIFF) -Nurp $@.save $@")
			$(DIFF) -Nurp $@.save $@ || $(TRUE)
            else
			($(call cmd_noat,DIFF,-Nurp,$@.save,$@))
			$(DIFF) -Nurp $@.save $@ || $(TRUE)
            endif
			$(call echol,$(LINE))
        endif
    endif
endif
		else
			$(call echol,"Unchanged:  $@")
		fi
	else
		($(call cmd_noat,INSTALL,$(bldtarget),$@,$(conf_perms),$(INST_OWNER),$(INST_GROUP)))
		rc=$$?
		if [ $${rc} -ne 0 ]; then
			$(call echol,"Error installing $@.")
			$(call echol,$(LINE))
			$(call echol,"Maybe you intended 'sudo make install' instead?")
			exit $${rc}
		fi
	fi

.ONESHELL: uninstall
.PHONY: uninstall
uninstall: 
	@for delFile in $(wildcard $(install_conf_files) $(patsubst %,%.new,$(install_conf_files)), $(patsubst %,%.save,$(install_conf_files)))
	do
		($(call cmd_noat,RM,$${delFile}))
		rc=$$?
		if [ $${rc} -ne 0 ];then
			$(call echol,"Error removing $${delFile}")
			$(call echol,"Giving up on $@.")
			$(call echol,$(LINE))
			$(call echol,"Maybe you intended 'sudo make $@' instead?")
			exit $${rc}
		fi
	done

# Restore any *.conf.save to *.conf
.ONESHELL: restore
.PHONY: restore
restore:
	@for savedFile in $(wildcard $(patsubst %,%.save,$(install_conf_files)))
	do
		origFile=$${savedFile%%.save}
		($(call cmd_noat,MV,$${savedFile},$${origFile}))
		rc=$$?
		if [ $${rc} -ne 0 ];then
			$(call echol,"Unable to restore $${savedFile} to $${origFile}")
			$(call echol,$(LINE))
			$(call echol,"Maybe you intended 'sudo make $@' instead?")
			exit $${rc}
		fi
	done
