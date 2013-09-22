#============================================================================
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
#============================================================================
.DEFAULT_GOAL := build

PROGRAM        = zensocket

# Define install-related attributes.

PROGRAM_PERMS  = 04750
PROGRAM_OWNER  = root
ZENHOME       ?= /opt/zenoss
PREFIX        ?= $(ZENHOME)/bin
PREFIX         = inst
INSTDIR        = $(DESTDIR)$(PREFIX)

# Define build-related attributes

OBJDIR              = obj
INCLUDE_SYSINC_DEPS = no
INCLUDE_DEBUG_SYMS  = yes
CC                  = gcc

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
# Primitive to use when installing files.
INSTALL  = install
LINE     = "-----------------------------------------------------------------------------"

#---------------------------------------------------------------------------#
# Configure gcc to dump out header files actually used at compile-time.
#---------------------------------------------------------------------------#

GCC_MAKE_DEPENDENCY_RULES = -M
ifeq "$(INCLUDE_SYSINC_DEPS)" "yes"
    SUPPRESS_SYSINC_DEPS =
else
    # Do not include system header directories (nor headers files that are
    # included directly or indirectly from such headers).  These hardly
    # ever change so making rebuilds sensitive to their modtimes is
    # usually overkill.
    SUPPRESS_SYSINC_DEPS = M
endif

# Give us control on the name of the dependency file (e.g., hello.d).
GCC_MAKE_DEP_FILENAME = -MF

# Work-around errors make gives if you remove header files without 
# updating the makefile to match.
GCC_MAKE_PHONY_TARGETS = -MP

# Override target of emitted dependency rule so we can include proper
# pathing to our objdir.
GCC_MAKE_MOD_TARGET_PATH  = -MT
GCC ?= gcc
# $(call make-depend,source-file,object-file,depend-file)
define make-depend 
    $(GCC) $(CFLAGS) $(CPPFLAGS) $(TARGET_ARCH) $1\
	$(GCC_MAKE_DEPENDENCY_RULES)$(SUPPRESS_SYSINC_DEPS)\
	$(GCC_MAKE_PHONY_TARGETS)    \
	$(GCC_MAKE_MOD_TARGET_PATH) $2  \
	$(GCC_MAKE_DEP_FILENAME) $3 
endef


#============================================================================
# Build Targets
#============================================================================
ifneq "$(MAKECMDGOALS)" "clean"
    -include $(OBJDIR)/$(PROGRAM).d
endif

.PHONY: all build 
all build: $(OBJDIR)/$(PROGRAM)

$(OBJDIR) $(INSTDIR):
	mkdir -p $@

$(OBJDIR)/$(PROGRAM): $(OBJDIR)/$(PROGRAM).o
	$(LINK.c) $^ $(LOADLIBES) $(LDLIBS) -o $@

$(OBJDIR)/$(PROGRAM).o: | $(PYTHON_INCDIR)
$(OBJDIR)/$(PROGRAM).o: | $(OBJDIR)
$(OBJDIR)/$(PROGRAM).o: $(PROGRAM).c
	$(call make-depend,$<,$@,$(subst .o,.d,$@))
	$(COMPILE.c) $(OUTPUT_OPTION) $<

OBJFILES = $(wildcard $(patsubst %,$(OBJDIR)/%,$(PROGRAM) $(PROGRAM).o $(PROGRAM).d))
.PHONY: clean
clean:
	@for objfile in $(OBJFILES);\
	do \
		echo "rm $${objfile}" ;\
		rm $${objfile} ;\
	done
	@count=`ls -a1 $(OBJDIR) 2>/dev/null|wc -l` ;\
	if ((count < 3 ));then \
		echo "rm -rf $(OBJDIR)" ;\
		rm -rf $(OBJDIR) ;\
	fi

.PHONY: install
install: | $(INSTDIR)
install:
	@if [ ! -f "$(OBJDIR)/$(PROGRAM)" ]; then \
		echo "Unable to install $(PROGRAM).  Missing $(OBJDIR)/$(PROGRAM)." ;\
		echo $(LINE) ;\
		echo "Run 'make build' first" ;\
		echo ;\
		exit 1 ;\
	fi
	@echo "$(INSTALL) -m $(PROGRAM_PERMS) -o $(PROGRAM_OWNER) $(OBJDIR)/$(PROGRAM) $(INSTDIR)"
	@if ! $(INSTALL) -m $(PROGRAM_PERMS) -o $(PROGRAM_OWNER) $(OBJDIR)/$(PROGRAM) $(INSTDIR) ;then \
		echo $(LINE) ;\
		echo "Try 'sudo make install'" ;\
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
