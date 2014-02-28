#============================================================================
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
#============================================================================
.DEFAULT_GOAL := help # all|build|clean|distclean|devinstall|install|help

#============================================================================
# Build component configuration.
#
# Beware of trailing spaces.
# Don't let your editor turn tabs into spaces or vice versa.
#============================================================================
COMPONENT = conf
confdirs  = etc zenoss

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
    include $(NEAREST_ZENMAGIC_MK)
endif

install_confdirs   := $(patsubst %,install-%,$(confdirs))
uninstall_confdirs := $(patsubst %,uninstall-%,$(confdirs))
restore_confdirs   := $(patsubst %,restore-%,$(confdirs))
settings_confdirs  := $(patsubst %,settings-%,$(confdirs))
mrclean_confdirs   := $(patsubst %,mrclean-%,$(confdirs))

help: dflt_component_help
	@echo Using common build idioms from $(NEAREST_ZENMAGIC_MK)
	@echo

.PHONY: build
build: $(confdirs)

.PHONY: $(confdirs)
$(confdirs): | $@
	@cd $@ && make --no-print-directory build bldtop=$(abspath build/$@)

.PHONY: clean
clean:
	@if [ -d "$(blddir)" ];then \
		if [ "$(abspath $(blddir))" != "$(abspath $(srcdir))" ];then \
			($(call cmd_noat,RMDIR,$(blddir))) ;\
			rc=$$? ;\
			if [ $${rc} -ne 0 ] ; then \
				echo $(LINE) ;\
				echo "Problem removing $(blddir)." ;\
				echo ;\
				exit $${rc} ;\
			fi ;\
		else \
			$(call echol,"Error: Ignorning request to remove the build directory which is") ;\
			$(call echol,"       currently the same as your source directory.") ;\
			$(call echol,$(LINE)) ;\
			$(call echol,"       blddir $(abspath $(blddir))") ;\
			$(call echol,"       srcdir $(abspath $(srcdir))") ;\
		fi ;\
	fi

.PHONY: mrclean
mrclean distclean: clean
	@if [ -f "$(COMPONENT).log" ];then \
		rm $(COMPONENT).log ;\
	fi

.PHONY: install
install: $(install_confdirs)

.ONESHELL: $(install_confdirs)
.PHONY: $(install_confdirs)
$(install_confdirs): confdir = $(patsubst install-%,%,$@)
$(install_confdirs): 
	@(cd $(confdir) && make --no-print-directory install bldtop=$(abspath build/$(confdir)))
	rc=$$?
	if [ $${rc} -ne 0 ] ; then
		echo $(LINE)
		echo "Maybe you intended 'sudo make install instead?"
		echo 
		exit $${rc}
	fi

.ONESHELL: $(restore_confdirs)
.PHONY: $(restore_confdirs)
$(restore_confdirs): confdir = $(patsubst restore-%,%,$@)
$(restore_confdirs): 
	@(cd $(confdir) && make --no-print-directory restore bldtop=$(abspath build/$(confdir)))
	rc=$$?
	if [ $${rc} -ne 0 ] ; then
		echo $(LINE)
		echo "Maybe you intended 'sudo make restore instead?"
		echo 
		exit $${rc}
	fi

.ONESHELL: uninstall
.PHONY: uninstall
uninstall: $(uninstall_confdirs)

.ONESHELL: $(uninstall_confdirs)
.PHONY: $(uninstall_confdirs)
$(uninstall_confdirs): confdir = $(patsubst uninstall-%,%,$@)
$(uninstall_confdirs): 
	@(cd $(confdir) && make --no-print-directory uninstall bldtop=$(abspath build/$(confdir)))
	rc=$$?
	if [ $${rc} -ne 0 ] ; then
		echo $(LINE)
		echo "Maybe you intended 'sudo make uninstall instead?"
		echo 
		exit $${rc}
	fi

.ONESHELL: settings
.PHONY: settings
settings: $(settings_confdirs)
$(settings_confdirs): confdir = $(patsubst settings-%,%,$@)
$(settings_confdirs):
	@cd $(confdir) && make --no-print-directory settings bldtop=$(abspath build/$(confdir))

.ONESHELL: mrclean
.PHONY: mrclean
mrclean: $(mrclean_confdirs)
$(mrclean_confdirs): confdir = $(patsubst mrclean-%,%,$@)
$(mrclean_confdirs):
	@cd $(confdir) && make --no-print-directory mrclean bldtop=$(abspath build/$(confdir))
