#============================================================================
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
#============================================================================
ifdef DEBUG_SHELL
    SHELL = /bin/shell -x -v
endif
# Assume the build component name is the same as the base directory name.  
#
# Can be overridden in the calling makefile via:
#
#    COMPONENT = my-crazy-component
#    include zenmagic.mk
#    ..
DFLT_COMPONENT := $(shell basename `pwd`)

ifeq "$(COMPONENT)" ""
    COMPONENT  := $(DFLT_COMPONENT)
endif
# Use this version internally as it avoids subtle errors introduced by 
# trailing whitespace.
_COMPONENT     := $(strip $(COMPONENT))

BUILD_LOG      ?= $(_COMPONENT).log
ABS_BUILD_LOG   = $(abspath $(BUILD_LOG))
ABS_BUILD_DIR   = $(abspath $(BUILD_DIR))
CHECKED_ENV    ?= .checkedenv


# Prompt before uninstalling a given component.  Nice since this usually
# involves wildcard removal of all the stuff in a common install directory.

SAFE_UNINSTALL ?= yes # yes|no
_SAFE_UNINSTALL = $(strip $(SAFE_UNINSTALL))

# If the install prefix has not been configured in, default to a 
# component-defined install directory.

ifndef PREFIX
    PREFIX ?= @prefix@
endif
ifeq "$(PREFIX)" "@prefix@"
    PREFIX := $(COMPONENT_PREFIX)
endif
ABS_PREFIX := $(abspath $(PREFIX))
# Flag _PREFIX to avoid edge case where we hit a circular dependency
# in the install target if the directory we're installing to is also called 'install'
ifeq "$(PREFIX)" "install"
    $(error "Using treacherous install directory name.  Must be something other than 'install')
else
    _PREFIX := $(PREFIX)
endif

# Normalize DESTDIR so we can use this idiom in our install targets:
#
#    $(_DESTDIR)$(_PREFIX)
#
# such that we don't end up with double slashes.
#
# DESTDIR is used for staged-installs, a requirement of packaged
# builds as a non-root user.
# 
# http://www.gnu.org/prep/standards/html_node/DESTDIR.html#DESTDIR

_DESTDIR = $(strip $(DESTDIR))
ifneq "$(_DESTDIR)" ""
    # Normalize _DESTDIR to include trailing slash if DESTDIR is non-null
    # (unless _PREFIX already begins with a leading slash).
    PREFIX_HAS_LEADING_SLASH = $(patsubst /%,/,$(_PREFIX))
    ifeq "$(PREFIX_HAS_LEADING_SLASH)" "/"
        _DESTDIR := $(shell echo $(_DESTDIR) | sed -e "s|\/$$||g")
    else
        _DESTDIR := $(shell echo $(_DESTDIR) | sed -e "s|\/$$||g" -e "s|$$|\/|g")
    endif
endif

# If the sysconfdir (e.g., etc) has not been configured in, default to a 
# component-defined sysconfdir.

SYSCONFDIR = @sysconfdir@
ifeq "$(SYSCONFDIR)" "@sysconfdir@"
    SYSCONFDIR = $(COMPONENT_SYSCONFDIR)
endif

# Distro.  This dies after configure comes online.  OSX, for example, has backlevel 
# command-line tools (circa 1999) that don't support modern options.
DISTRO := $(shell uname -s)

#============================================================================
# BUILD TOOLS
#============================================================================

#----------------------------------------------------------------------------
# Isolate build primitives for easy global redefinition.
#----------------------------------------------------------------------------
AWK          = awk
BC           = bc
CP           = cp
CUT          = cut
DATE         = date
EGREP        = egrep
FIND         = find
GREP         = grep
HEAD         = head
INSTALL      = install
JAVA         = java
LN           = ln
MKDIR        = mkdir
MVN          = mvn
PR           = pr
RM           = rm
SED          = sed
SORT         = sort
TAR          = tar
TEE          = tee
TOUCH        = touch
TR           = tr
XARGS        = xargs

# Making use of .ONESHELL to simplify multi-line rules.
# http://www.electric-cloud.com/blog/2010/08/03/gnu-make-3-82-is-out/
REQD_MAKE_MIN_VER = 3.82
REQD_MAKE_BRAND   = GNU
CHECK_TOOLS_VERSION_BRAND += make:$(REQD_MAKE_MIN_VER):$(REQD_MAKE_BRAND)

ifndef CHECK_TOOLS

    # Avoid odd error messages when the build ecosystem is incomplete by iterating
    # over a list of required build tools.  This can go away once we have a configure
    # script in place.
    #
    # Easy to override at component level for component-specific tool sets.

    CHECK_TOOLS := $(AWK)  $(CUT) $(DATE)  $(EGREP) $(FIND) $(HEAD) 
    CHECK_TOOLS += $(JAVA) $(LN)  $(MKDIR) $(MVN)   $(PR)   $(RM)
    CHECK_TOOLS += $(SED)  $(SORT) $(TAR) $(TEE)   $(TOUCH) $(XARGS)

endif
CHECK_TOOLS += $($(_COMPONENT)_CHECK_TOOLS)

# Default idiom for specifying the source associated with a given target.
ifeq "$(COMPONENT_SRC)" ""
    DFLT_COMPONENT_SRC := $(shell $(FIND) $(SRC_DIR) -type f)
endif


ifeq "$(REQUIRES_JDK)" "1"
    POM ?= pom.xml

    # These become subsitution variables once our configure script is aware
    # of this makefile.
    REQD_JDK_MIN_VER   = 1.7.0
    #REQD_JDK_BRAND    = OpenJDK
    REQD_MVN_MIN_VER   = 3.0.0
    #REQD_MVN_BRAND    = Apache

    CHECK_TOOLS_VERSION_BRAND += java:$(REQD_JDK_MIN_VER):$(REQD_JDK_BRAND) mvn:$(REQD_MVN_MIN_VER):$(REQD_MVN_BRAND)

    DFLT_MAVEN_OPTS = -DskipTests
    ifndef MAVEN_OPTS
        ifndef $(_COMPONENT)_MAVEN_OPTS
            MAVEN_OPTS ?= $(DFLT_MAVEN_OPTS)
        else
            MAVEN_OPTS  = $($(_COMPONENT)_MAVEN_OPTS)
        endif
    else
        MAVEN_OPTS := $($(_COMPONENT)_MAVEN_OPTS) $(MAVEN_OPTS)
    endif

    # Trust that maven will only rebuild when necessary.  
    # Otherwise, rely upon make's somewhat naive view of when to rebuild.
    TRUST_MVN_REBUILD  = yes # yes|no
    _TRUST_MVN_REBUILD = $(strip $(TRUST_MVN_REBUILD))

    ifeq "$(COMPONENT_JAR)" ""
        # Derive the filename of the component jar/tar we're trying to build:
        #
        #    e.g., <component>-x.y.z-jar
        #          <component>-x.y.z-zapp.tar.gz
        #
        # by parsing the toplevel pom.xml.
        #
        DFLT_COMPONENT_JAR := $(shell $(GREP) -C4 "<artifactId>$(_COMPONENT)</artifactId>" $(POM) | $(GREP) -A3 "<groupId>[orgcom]*.zenoss</groupId>" | $(EGREP) "groupId|artifactId|version" |$(CUT) -d">" -f2 |$(CUT) -d"<" -f1|$(XARGS) echo|$(SED) -e "s|.*zenoss \([^ ]*\) \([^ ]*\)|\1-\2.jar|g"|$(HEAD) -1)
    endif
endif
# Enforce presence of component-specific tools (i.e., that require certain version / brand).
CHECK_TOOLS_VERSION_BRAND += $($(_COMPONENT)_CHECK_TOOLS_VERSION_BRAND)

DATA_FILE_PERMS    = 644
EXEC_FILE_PERMS    = 755
INSTALL_PROGRAM    = $(INSTALL) -m $(EXEC_FILE_PERMS)
INSTALL_DATA       = $(INSTALL) -m $(DATA_FILE_PERMS)
LINE77            := "-----------------------------------------------------------------------------"
LINE              := $(LINE77)

#----------------------------------------------------------------------------
# Control the verbosity of the build.  
#
# By default we build in 'quiet' mode so there is more emphasis on noticing
# and resolving warnings.
#
# Use 'make V=1 <target>' to see the actual commands invoked during a build.
#----------------------------------------------------------------------------
ifdef V
    ifeq ("$(origin V)", "command line")
        ZBUILD_VERBOSE = $(V)
    endif
endif

ifndef ZBUILD_VERBOSE
    ZBUILD_VERBOSE = 0
endif

ifeq ($(ZBUILD_VERBOSE),1)
    quiet =
    Q =
else
    quiet=quiet_
    Q = @
endif

#
# If the user is running make -s (silent mode), suppress echoing of
# commands.
# 
ifneq ($(findstring s,$(MAKEFLAGS)),)
    quiet=silent_
endif

#----------------------------------------------------------------------------
# Define the 'cmd' macro that controls verbosity of build output.
#
# Normally we're in 'quiet' mode meaning we just echo out the short version 
# of the command before running the full command.
#
# In verbose mode, we echo out the full command and run it as well.
# 
# Requires commands to define these macros:
#
#    quite_cmd_BLAH = BLAH PSA $@
#          cmd_BLAH = actual_blah_cmd ...
#----------------------------------------------------------------------------

TIME_TAG=[$(shell $(DATE) +"%H:%M")]

ifeq "$(ZBUILD_VERBOSE)" "1"
    #--------------------------------------------------------------
    # For verbose builds, we echo the raw command and stdout/stderr
    # to the console and log file.
    #--------------------------------------------------------------
    cmd = @$(if $($(quiet)cmd_$(1)),\
        echo '  $(TIME_TAG)  $($(quiet)cmd_$(1))  ' &&) $(cmd_$(1)) 2>&1 | $(TEE) -a $(BUILD_LOG)
    cmd_noat = $(if $($(quiet)cmd_$(1)),\
        echo '  $(TIME_TAG)  $($(quiet)cmd_$(1))  ' &&) $(cmd_$(1)) 2>&1 | $(TEE) -a $(BUILD_LOG)
else
    #--------------------------------------------------------------
    # For quiet builds, we present abbreviated output to the console.
    # Build log contains full command plus stdout/stderr.
    #--------------------------------------------------------------
    cmd = @$(if $($(quiet)cmd_$(1)),\
        echo '  $(TIME_TAG)  $($(quiet)cmd_$(1))  ' &&) (echo '$(cmd_$(1))' ;$(cmd_$(1))) 2>&1 >>$(BUILD_LOG) || (echo "  $(TIME_TAG)  ERROR: See $(ABS_BUILD_LOG) for details."; echo ; exit 1)
    cmd_noat = $(if $($(quiet)cmd_$(1)),\
        echo '  $(TIME_TAG)  $($(quiet)cmd_$(1))  ' &&) (echo '$(cmd_$(1))' ;$(cmd_$(1))) 2>&1 >>$(BUILD_LOG) || (echo "  $(TIME_TAG)  ERROR: See $(ABS_BUILD_LOG) for details."; echo  ; exit 1)
endif

#----------------------------------------------------------------------------
# Echo and log.
define echol
    echo "  $(TIME_TAG)  "$1 | $(TEE) -a $(BUILD_LOG)
endef

#----------------------------------------------------------------------------
# Remove a file.
quiet_cmd_CP = CP     $2 $3
      cmd_CP = $(CP) $2 $3

#----------------------------------------------------------------------------
# Remove a file.
quiet_cmd_INSTALL = INSTALL [m=$4 o=$5 g=$6] $3
      cmd_INSTALL = $(INSTALL) -m $4 -o $5 -g $6 $2 $3

#----------------------------------------------------------------------------
# Make a directory.
quiet_cmd_MKDIR = MKDIR  $2
      cmd_MKDIR = $(MKDIR) -p $2

#------------------------------------------------------------
# Invoke maven <arg>.
quiet_cmd_MVN = MVN    $2 $3
      cmd_MVN = $(MVN) $(MAVEN_OPTS) $2 

quiet_cmd_MVNASM = MVN    assemble $3
      cmd_MVNASM = $(MVN) $(MAVEN_OPTS) $2 

#----------------------------------------------------------------------------
# Remove a file.
quiet_cmd_RM = RM     $2
      cmd_RM = $(RM) -f "$2"

#----------------------------------------------------------------------------
# Remove a directory.
quiet_cmd_RMDIR = RMDIR  $2
      cmd_RMDIR = $(RM) -rf "$2"

#----------------------------------------------------------------------------
# Remove a directory in a safe way.
#    -I prompt once before removing more than 3 files (in case a dangerous
#       install prefix was specified).
ifeq "$(_SAFE_UNINSTALL)" "yes"
    ifeq "$(DISTRO)" "Darwin"
        SAFE_RM_OPTS = -i
    else
        SAFE_RM_OPTS = -I --preserve-root
    endif
else
    ifneq "$(DISTRO)" "Darwin"
        SAFE_RM_OPTS = --preserve-root
    endif
endif
quiet_cmd_SAFE_RMDIR = RMDIR  $2
ifeq "$(_SAFE_UNINSTALL)" "yes"
      cmd_SAFE_RMDIR = $(RM) -r $(SAFE_RM_OPTS) "$2"
else
      cmd_SAFE_RMDIR = $(RM) -r $(SAFE_RM_OPTS) "$2"
endif

#------------------------------------------------------------
# sed
quiet_cmd_SED = SED    $5   $4
      cmd_SED = $(SED) $2 $3 > $4

#------------------------------------------------------------
# symlink
quiet_cmd_SYMLINK = SYMLNK $3 -> $2
      cmd_SYMLINK = $(LN) -sf $2 $3

#------------------------------------------------------------
# Create a tar.gz file.  Remove suspect or empty archive on error.
quiet_cmd_TAR = TAR   $@
      cmd_TAR = ($(TAR) zcvf $@ -C "$2" $3) || $(RM) -f "$@"

#----------------------------------------------------------------------------
# Touch a file
quiet_cmd_TOUCH = TOUCH  $2
      cmd_TOUCH = $(TOUCH) $2

#----------------------------------------------------------------------------
# Untar something into an existing directory
quiet_cmd_UNTAR = UNTAR  $2 -> $3
      cmd_UNTAR = $(TAR) -xvf $2 -C $3

#----------------------------------------------------------------------------
# Verify that required build tools are present in the environment.
#----------------------------------------------------------------------------
CHECKED_TOOLS = .checkedtools
$(CHECKED_TOOLS):
	@for tool in $(CHECK_TOOLS) ;\
	do \
		if [ "$(ZBUILD_VERBOSE)" = "1" ];then \
			$(call echol,"which $${tool}") ;\
		else \
			$(call echol,"CHKBIN $${tool}") ;\
		fi ;\
		if ! which $${tool} 2>/dev/null 1>&2; then \
			$(call echol,"ERROR: Missing $${tool} from search path.") ;\
			exit 1 ;\
		fi ;\
	done
	$(call cmd,TOUCH,$@)

#----------------------------------------------------------------------------
# Verify that certain build tools are at the correct version and brand.
# (e.g., OpenJDK 1.7)
#----------------------------------------------------------------------------
CHECKED_TOOLS_VERSION_BRAND = .checkedtools_version_brand
$(CHECKED_TOOLS_VERSION_BRAND):
	@for tool_version_brand in $(CHECK_TOOLS_VERSION_BRAND) ;\
	do \
		tool=`echo $${tool_version_brand} | cut -d":" -f1`;\
		case "$${tool}" in \
			"java") \
				dotted_min_desired_ver=`echo $${tool_version_brand} | cut -d":" -f2` ;\
				min_desired_ver=`echo $${dotted_min_desired_ver} |tr "." " "|$(AWK) '{printf("(%d*100)+(%d*10)+(%d)\n",$$1,$$2,$$3)}'|$(BC)` ;\
				dotted_actual_ver=`$(JAVA) -version 2>&1 | grep "^java version" | $(AWK) '{print $$3}' | tr -d '"' | tr -d "'" | cut -d"." -f1-3|cut -d"_" -f1` ;\
				actual_ver=`echo $${dotted_actual_ver} |tr "." " "|$(AWK) '{printf("(%d*100)+(%d*10)+(%d)\n",$$1,$$2,$$3)}'|$(BC)` ;\
				$(call echol,"CHKVER $${tool} >= $${dotted_min_desired_ver}") ;\
				if [ $${actual_ver} -lt $${min_desired_ver} ];then \
					$(call echol,"ERROR: java version is $${dotted_actual_ver}  Expecting version  >= $${dotted_min_desired_ver}") ;\
					exit 1;\
				else \
					desired_brand=`echo $${tool_version_brand} | cut -d":" -f3` ;\
					actual_brand=`$(JAVA) -version 2>&1 | grep -v java | awk '{print $$1}' | sort -u | grep -i jdk` ;\
					if [ ! -z "$${desired_brand}" -a "$${actual_brand}" != "$${desired_brand}" ];then \
						$(call echol,"ERROR: jdk brand is $${actual_brand}.  Expecting $${desired_brand}.") ;\
						exit 1;\
					fi ;\
				fi ;\
				;;\
			"make") \
				dotted_min_desired_ver=`echo $${tool_version_brand} | cut -d":" -f2` ;\
				min_desired_ver=`echo $${dotted_min_desired_ver} |tr "." " "|$(AWK) '{printf("(%d*100)+(%d*10)+(%d)\n",$$1,$$2,$$3)}'|$(BC)` ;\
				dotted_actual_ver=`make -v 2>&1 | head -1 | $(AWK) '{print $$3}' | tr -d '"' | tr -d "'"` ;\
				actual_ver=`echo $${dotted_actual_ver} |tr "." " "|$(AWK) '{printf("(%d*100)+(%d*10)+(%d)\n",$$1,$$2,$$3)}'|$(BC)` ;\
				$(call echol,"CHKVER $${tool}  >= $${dotted_min_desired_ver}") ;\
				if [ $${actual_ver} -lt $${min_desired_ver} ];then \
					$(call echol,"ERROR: make version is $${dotted_actual_ver}  Expecting version  >= $${dotted_min_desired_ver}") ;\
					$(call echol,"       Upgrade to avoid vexing 'unexpected end of file' errors.") ;\
					exit 1;\
				else \
					desired_brand=`echo $${tool_version_brand} | cut -d":" -f3` ;\
					actual_brand=`make -v 2>&1 | head -1 | awk '{print $$1}'` ;\
					if [ ! -z "$${desired_brand}" -a "$${actual_brand}" != "$${desired_brand}" ];then \
						$(call echol,"ERROR: make brand is $${actual_brand}.  Expecting $${desired_brand}.") ;\
						$(call echol,"ERROR: make brand is $${actual_brand}.  Expecting $${desired_brand}.") ;\
						exit 1;\
					fi ;\
				fi ;\
				;;\
			"mvn") \
				dotted_min_desired_ver=`echo $${tool_version_brand} | cut -d":" -f2` ;\
				min_desired_ver=`echo $${dotted_min_desired_ver} |tr "." " "|$(AWK) '{printf("(%d*100)+(%d*10)+(%d)\n",$$1,$$2,$$3)}'|$(BC)` ;\
				dotted_actual_ver=`$(MVN) -version 2>&1 | head -1 | $(AWK) '{print $$3}' | tr -d '"' | tr -d "'" | cut -d"." -f1-3|cut -d"_" -f1` ;\
				actual_ver=`echo $${dotted_actual_ver} |tr "." " "|$(AWK) '{printf("(%d*100)+(%d*10)+(%d)\n",$$1,$$2,$$3)}'|$(BC)` ;\
				$(call echol,"CHKVER $${tool}  >= $${dotted_min_desired_ver}") ;\
				if [ $${actual_ver} -lt $${min_desired_ver} ];then \
					$(call echol,"ERROR: mvn version is $${dotted_actual_ver}  Expecting version  >= $${dotted_min_desired_ver}") ;\
					exit 1;\
				else \
					desired_brand=`echo $${tool_version_brand} | cut -d":" -f3` ;\
					actual_brand=`$(MVN) -version 2>&1 | head -1 | awk '{print $$1}'` ;\
					if [ ! -z "$${desired_brand}" -a "$${actual_brand}" != "$${desired_brand}" ];then \
						$(call echol,"ERROR: mvn brand is $${actual_brand}.  Expecting $${desired_brand}.") ;\
						exit 1;\
					fi ;\
				fi ;\
				;;\
		esac ;\
	done
	$(call cmd,TOUCH,$@)

.PHONY: checkenv
checkenv: $(CHECKED_ENV)
$(CHECKED_ENV): | $(CHECKED_TOOLS) $(CHECKED_TOOLS_VERSION_BRAND)
	$(call cmd,TOUCH,$@)
	@$(call echol,"BLDLOG $(ABS_BUILD_LOG)")
	@echo $(LINE)

.PHONY: dflt_component_help
dflt_component_help:
	@echo
	@echo "Zenoss 5.x $(_COMPONENT) makefile"
	@echo
	@echo "Usage: make <target>"
	@echo "       make <target> V=1  # for verbose output"
	@echo
	@echo "where <target> is one or more of the following:"
	@echo $(LINE)
	@make -rpn | $(SED) -n -e '/^$$/ { n ; /^[^ ]*:/p ; }' | $(EGREP) -v ".PHONY|:=|^\[|^\"|^\@|^\.|^echo"| $(SORT) |\
	$(SED) -e "s|:.*||g" | $(EGREP) -v "^\.|^$(BUILD_DIR)\/|install|^$(PREFIX)\/|^\/|^dflt_|clean|\.|\/" | $(PR) -t -w 80 -3
	@echo $(LINE)
	@make -rpn | $(SED) -n -e '/^$$/ { n ; /^[^ ]*:/p ; }' | $(EGREP) -v ".PHONY" | $(SORT) |\
	$(SED) -e "s|:.*||g" | $(EGREP) -v "^\.|^$(BUILD_DIR)\/|^$(PREFIX)\/|^\/|^dflt_|clean|\.|\/" | $(EGREP) "^install|^devinstall" | $(PR) -t -w 80 -3
	@echo $(LINE)
	@make -rpn | $(SED) -n -e '/^$$/ { n ; /^[^ ]*:/p ; }' | $(EGREP) -v ".PHONY" | $(SORT) |\
	$(SED) -e "s|:.*||g" | $(EGREP) -v "^\.|^$(BUILD_DIR)\/|^$(PREFIX)\/|^\/|^dflt_|\.|\/" | $(EGREP) "^clean|^un|clean" |  $(PR) -t -w 80 -3
	@echo $(LINE)
	@echo "Build results logged to $(BUILD_LOG)."

.PHONY: dflt_devinstall
dflt_devinstall: parent_target = $(shell echo $@ | sed -e "s/dflt_//g")
dflt_devinstall:
	@echo "$(parent_target) not implemented yet.  You're smart and good looking.  Teach me how to do $(parent_target)?"

.PHONY: dflt_component_uninstall
dflt_component_uninstall:
	@if [ -d "$(_DESTDIR)$(_PREFIX)" ];then \
		$(call cmd_noat,SAFE_RMDIR,$(_DESTDIR)$(_PREFIX)) ;\
		$(call echol,$(LINE)) ;\
		$(call echol,"$(_COMPONENT) uninstalled from $(_DESTDIR)$(_PREFIX)") ;\
	fi

.PHONY: dflt_component_clean
dflt_component_clean: 
ifeq "$(REQUIRES_JDK)" "1"
	$(call cmd,MVN,clean)
endif

.PHONY: dflt_component_mrclean dflt_component_distclean
dflt_component_mrclean dflt_component_distclean: dflt_component_clean
	@if [ -f "$(CHECKED_TOOLS_VERSION_BRAND)" ]; then \
		$(call cmd_noat,RM,$(CHECKED_TOOLS_VERSION_BRAND)) ;\
	fi
	@if [ -f "$(CHECKED_TOOLS)" ]; then \
		$(call cmd_noat,RM,$(CHECKED_TOOLS)) ;\
	fi
	@if [ -f "$(CHECKED_ENV)" ]; then \
		$(call cmd_noat,RM,$(CHECKED_ENV)) ;\
	fi
	@if [ -f "$(BUILD_LOG)" ]; then \
		$(RM) $(BUILD_LOG) ;\
	fi
