#============================================================================
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
#============================================================================
.DEFAULT_GOAL := build

PROGRAM        = pyraw

# Define install-related attributes.

PROGRAM_PERMS  = 04750
PROGRAM_OWNER  = root
ZENHOME       ?= /opt/zenoss
PREFIX        ?= $(ZENHOME)/bin
INSTDIR        = $(DESTDIR)$(PREFIX)

# Define build-related attributes

OBJDIR                   = obj
WITH_ZENOSS_PYTHON_DEVEL = yes
INCLUDE_SYSINC_DEPS      = no
PYTHON_MAJ_MIN_VER       = 2.7


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

    PYTHON_INCDIR  = $(DESTDIR)$(ZENHOME)/include/python$(PYTHON_MAJ_MIN_VER)
    PYTHON_LIBDIR  = $(DESTDIR)$(ZENHOME)/lib

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
    RPATH_OPT       = -Wl,-rpath,$(LIBPYTHON_RPATH) -Wl,-z,origin
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

INSTFILES = $(wildcard $(patsubst %,$(INSTDIR)/%,$(PROGRAM)))
.PHONY: uninstall
uninstall:
	$(foreach instfile,$(INSTFILES),rm $(instfile);)
