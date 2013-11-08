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
COMPONENT = bin
programs  = python pyraw zensocket
scripts   = scripts

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
    #ifneq "$(MAKECMDGOALS)" ""
    #    $(warning "Including $(NEAREST_ZENMAGIC_MK) $(MAKECMDGOALS)")
    #endif
    include $(NEAREST_ZENMAGIC_MK)
endif

install_programs     := $(patsubst %,install-%,$(programs))
installhere_programs := $(patsubst %,installhere-%,$(programs))

install_scripts      := $(patsubst %,install-%,$(scripts))
installhere_scripts  := $(patsubst %,installhere-%,$(scripts))

help: dflt_component_help
	@echo Using common build idioms from $(NEAREST_ZENMAGIC_MK)
	@echo

.PHONY: build
build: $(programs) $(scripts)

.PHONY: $(programs)
python: | $@
	cd $@ && make build export bldtop=$(abspath build/$@)

$(filter-out python,$(programs)): | $@
	cd $@ && make build blddir=$(abspath build/$@)

.PHONY: $(scripts)
$(scripts): | $@
	cd $@ && make build bldtop=$(abspath build/$@)

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
	@if [ -d "$(_DESTDIR)$(bindir)" ];then \
		count=$(shell ls -a1 $(_DESTDIR)$(bindir) 2>/dev/null|wc -l) ;\
		if ((count >= 3 ));then \
			echo "You may also run 'make uninstall' to uninstall $(_DESTDIR)$(bindir)" ;\
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
install : $(install_programs) $(install_scripts)
installhere : $(installhere_programs) $(installhere_scripts)

.PHONY: $(install_programs)
$(install_programs): program = $(patsubst install-%,%,$@)
$(install_programs): 
	cd $(program) && make install blddir=$(abspath build/$(program)) 

$(installhere_programs): program = $(patsubst installhere-%,%,$@)
$(installhere_programs): 
	cd $(program) && make installhere blddir=$(abspath build/$(program)) DESTDIR=$(abspath $(heredir))

.PHONY: $(install_scripts)
$(install_scripts): script = $(patsubst install-%,%,$@)
$(install_scripts): 
	cd $(script) && make install bldtop=$(abspath build/$(script))

$(installhere_scripts): script = $(patsubst installhere-%,%,$@)
$(installhere_scripts): 
	cd $(script) && make installhere bldtop=$(abspath build/$(script)) DESTDIR=$(abspath $(heredir))

.PHONY: devinstall
devinstall: dflt_devinstall

.ONESHELL: uninstall
.PHONY: uninstall
uninstall:
	@if [ -d "$(_DESTDIR)$(bindir)" ]; then \
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
uninstallhere:
	@if [ -d "$(heredir)" ];then \
		$(call cmd_noat,RMDIR,$(heredir)) ;\
	fi
