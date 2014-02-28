# ============================================================================
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
# ============================================================================

# Set the shell to bash since we depend upon its PIPESTATUS feature for
# managing exit status from within our tersification and logging 'cmd' macro.
#
SHELL := $(shell /usr/bin/which bash)

# Specify the package name (which roughly equates to a product name).
#
# This influences where the product is installed via the prefix variable 
# defined below:
#
#    prefix = /opt/${package}
#
package := zenoss

# ============================================================================
# BUILD CONFIGURATION
# ============================================================================

# Specify if this is a production or development build through a profile
# macro.
#
# The profile is given meaning in the top-level and component-level makefiles 
# and may influence the build to be manifest-driven or discovery-driven in 
# personality.  
#
# This switch may enable development work-flows where, for example, 
# a group of 'installed' python modules are actually symlinks back to a 
# version controlled working directory.  This minimizes development overhead
# for diff'ing code and committing to a source repo after live debugging.
#
profile := prod

# Specify if the filesystem for the build supports hard linking.
#
# Some components (e.g., python built from source) assume the ability to
# hard link, but we may have to work around this in cases where the
# build is happening in a virtual machine but the source is mounted from
# a filesystem exported by the host.
#
fs_supports_hardlinking = yes

# Specify if the python used during the build (and installed with Zenoss) is
# derived from a virtualenv or built from source.
#
with_virtualenv = yes

# ============================================================================
# CANONICAL BUILD DIRECTORIES
# ============================================================================
prefix      ?= /usr/local/${package}
exec_prefix  = ${prefix}
bindir       = ${exec_prefix}/bin
sbindir      = ${exec_prefix}/sbin

srcdir      ?= .
blddir      ?= build
distdir     ?= dist

pkgconfdir   = ${prefix}/etc
sysconfdir   = /etc

pkgsrcdir   ?= src

# ============================================================================
# BUILD TOOLS
# ============================================================================

AWK          = awk
BC           = bc
CHMOD        = chmod
CHOWN        = chown
CMP          = cmp
CP           = cp
CURL         = curl
CUT          = cut
DATE         = date
DIFF         = diff
EASY_INSTALL = easy_install
EGREP        = egrep
FALSE        = false
FIND         = find
GCC         ?= gcc
CC           = $(GCC)
GREP         = grep
HEAD         = head
ID           = id
INSTALL      = install
JAVA         = java
LN           = ln
MAKE         = make
MKDIR        = mkdir
MVN          = mvn
MV           = mv
PIP          = pip
PKGPYTHON    = python
PR           = pr
PRINTF       = printf
#PYTHON      = python
READELF      = readelf
RM           = rm
SED          = sed
SORT         = sort
TAR          = tar
TEE          = tee
TOUCH        = touch
TR           = tr
TRUE         = true
VIRTUALENV   = virtualenv
SYSPYTHON    = /usr/bin/python
XARGS        = xargs
XPATH        = xpath


DFLT_COMPONENT     := $(shell basename `pwd`)
DFLT_COMPONENT_SRC := $(shell $(FIND) $(pkgsrcdir) -type f 2> /dev/null || echo "")

COMPONENT          ?= $(DFLT_COMPONENT)
_COMPONENT         := $(strip $(COMPONENT))

ifeq "$(REQUIRES_JDK)" "1"
    DFLT_JVM_OPTS          = -DskipTests --global-settings=/home/zendev/sb/platform-build/settings.xml
    ifndef JVM_OPTS
        ifndef $(_COMPONENT)_JVM_OPTS
            JVM_OPTS      ?= $(DFLT_JVM_OPTS)
        else
            JVM_OPTS       = $($(_COMPONENT)_JVM_OPTS)
        endif
    else
        JVM_OPTS          := $($(_COMPONENT)_JVM_OPTS) $(JVM_OPTS)
    endif    

    TRUST_MVN_REBUILD      = yes
    POM                   ?= pom.xml
    VERSION_PATH           = "//project/version/text()"

    DFLT_COMPONENT_NAME    := $(_COMPONENT)
    DFLT_COMPONENT_VERSION := $(shell $(XPATH) -q -e $(VERSION_PATH) $(POM))
    DFLT_COMPONENT_JAR      = $(COMPONENT_NAME)-$(COMPONENT_VERSION).jar
    DFLT_COMPONENT_TAR      = $(COMPONENT_NAME)-$(COMPONENT_VERSION)-zapp.tar.gz
endif

ifeq "$(REQUIRES_PYTHON)" "1"
    DFLT_COMPONENT_NAME    := $(shell $(PKGPYTHON) setup.py --name)
    DFLT_COMPONENT_VERSION := $(shell $(PKGPYTHON) setup.py --version)
    DFLT_COMPONENT_TAR     := $(shell $(PKGPYTHON) setup.py --fullname).tar.gz
endif
REQD_PYTHON_MIN_VER=2.7.2

# Assume the build component name is the same as the base directory name.
# Can be overridden in calling the makefile via:
#
#     COMPONENT = my-crazy-component
#     include zenmagic.mk
#     ..
COMPONENT_NAME    ?= $(DFLT_COMPONENT_NAME)
COMPONENT_VERSION ?= $(DFLT_COMPONENT_VERSION)
COMPONENT_SRC     ?= $(DFLT_COMPONENT_SRC)
COMPONENT_JAR     ?= $(DFLT_COMPONENT_JAR)
COMPONENT_TAR     ?= $(DFLT_COMPONENT_TAR)

BUILD_LOG         ?= $(_COMPONENT).log
ABS_BUILD_LOG      = $(abspath $(BUILD_LOG))
ABS_BUILD_DIR      = $(abspath $(blddir))

# ----------------------------------------------------------------------------
# Normally DESTDIR is a passthrough and prepends the install prefix, enabling
# staged installs (typically needed during package creation).
#
# Here, we hijack DESTDIR to implement a simple sandbox-relative install
# capability that doesn't require root privileges.
#
#    make installhere  --installs here:--> ./here/opt/zenoss/*
#
# Alternatively,
#
#    sudo make install --installs here:--> /opt/zenoss/*
#
# Optionally,
#
#    export DESTDIR=/var/tmp
#    sudo make install --installs here:--> /var/tmp/opt/zenoss/*
#
# @see http://www.gnu.org/prep/standards/html_node/DESTDIR.html#DESTDIR
# ----------------------------------------------------------------------------
heretoken  := here
_heretoken := $(strip $(heretoken))
heredir    := ./$(_heretoken)

# Turn install, uninstall, etc --into--> installhere, uninstallhere, ..
tokens     := install uninstall devinstall devuninstall
append-here-targets := $(patsubst %,%$(_heretoken),$(tokens))

ifneq "$(filter $(append-here-targets),$(MAKECMDGOALS))" ""

    # Hit this path if the user typed: 'make installhere|uninstallhere|..'
    #
    # During a dev work-flow, you may want to do an install under a sandbox-
    # relative directory as a preview to a package-level install.
    #
    # This is done by hijacking DESTDIR which is ideally suited for restaging
    # an install, as is done here.
    
    ifeq "$(DESTDIR)" ""
        _DESTDIR := $(strip $(heredir))
    else

        # Cases where the 'here' directory is relative to some parent
        # component. Honor whatever is passed via DESTDIR.
        _DESTDIR := $(strip $(DESTDIR))
    endif
else

    # If doing a normal 'make install', allow the DESTDIR environment variable
    # to pass through. If it is not defined, it will have no impact on the
    # install directory
    _DESTDIR = $(strip $(DESTDIR))
endif

# Normalize DESTDIR so we can use this idiom in our install targets:
#
# $(_DESTDIR)$(prefix)
#
# and not end up with double slashes.
ifneq "$(_DESTDIR)" ""
    PREFIX_HAS_LEADING_SLASH = $(patsubst /%,/,$(prefix))
    ifneq "$(PREFIX_HAS_LEADING_SLASH)" "/"
        _DESTDIR := $(shell echo $(_DESTDIR) | sed -e "s|\/$$||g")
    else
        _DESTDIR := $(shell echo $(_DESTDIR) | sed -e "s|\/$$||g" -e "s|$$|\/|g")
    endif
endif


CONF_FILE_PERMS = 600
DATA_FILE_PERMS = 644
EXEC_FILE_PERMS = 755
INSTALL_PROGRAM = $(INSTALL) -m $(EXEC_FILE_PERMS)
INSTALL_DATA    = $(INSTALL) -m $(DATA_FILE_PERMS)
LINE            = `$(PRINTF) '%77s\n' | $(TR) ' ' -`
LINE60          = `$(PRINTF) '%60s\n' | $(TR) ' ' -`

# Set the owner and the group for the install.
ifndef INST_OWNER
    ifeq "$(USER)" "root"
        INST_OWNER := $(or $(SUDO_USER), $(USER))
    else
        INST_OWNER := $(USER)
    endif
endif

ifndef INST_GROUP
    ifeq "$(SUDO_USER)" ""
        INST_GROUP := $(shell $(ID) -g -n $(USER))
    else
        INST_GROUP := $(shell $(ID) -g -n $(SUDO_USER))
    endif
endif

# ============================================================================
# LOGGING AND OUTPUT
# ============================================================================

# ----------------------------------------------------------------------------
#  Control the verbosity of the build
#
#  By default we build in 'quiet' mode so there is more emphasis on noticing
#  and resolving warnings.
#
#  Use 'make V=1 <target> to see the actual commands invoked durin a build.
# ----------------------------------------------------------------------------

ifdef V
    ifeq ("$(origin V)", "command line")
        ZBUILD_VERBOSE = $(V)
    endif
endif

ifneq ($(findstring s, $(MAKEFLAGS)), )
    ZBUILD_SILENT = 1
endif

ifeq "$(ZBUILD_VERBOSE)" "1"
    q =
    Q =
else
    q = quiet_
    Q = @
endif

# If the user is running in silent mode (e.g., make -s), suppress echoing of commands.
ifeq "$(ZBUILD_SILENT)" "1"
    q = silent_
endif

# ----------------------------------------------------------------------------
#  Define the 'cmd' macro that enables terse output to the console and full
#  output to a build log.
#
#  Normally we're in 'quiet' mode meaning we just echo the terse version of
#  the command to the console before running the full command.
#
#  In verbose mode, we echo the full command and run it as well.
#
#  Requires commands to define these macros:
#
#      quiet_cmd_BLAH = BLAH PSA $@
#            cmd_BLAH = actual_blah_cmd ...
# ----------------------------------------------------------------------------

# ------------------------------------------------------------------------
# Use the PIPESTATUS feature of bash to capture the exit status of 
# the first command in a pipeline of commands:
#
#    gcc | .. | tee -a build.log
#     ^
#     |
#     +---- gcc exit status == ${PIPESTATUS[0]}
#
# This allows us to capture the return code from the underlying build
# command (i.e., gcc, mvn) and bubble /that/ back up as the exit status
# of the tersified macro that wrappers the command.
#
# Otherwise, we would lamely return with the exit status of the last 
# command in the pipeline which, in our case, is the uninteresting 
# logging process, tee.  The undesirable effect would be to mask build 
# failures when they occur.
#
# You'll also notice the last expression in the macro has some
# conditional logic:
#
# CMD_RC=$${PIPESTATUS[0]}; if [ $${CMD_RC} -ne 0 ];then exit $${CMD_RC}; fi
#
# Here we /selectively/ exit only if the underlying cmd fails.  
# Otherwise we are prone to exiting a rule prematurely.  
#
# For example:
#
# Rule                 Rule with macro expansion
# -------------------  -------------------------------------
# target: dep          target: dep
#    $(call cmd,GCC)      gcc .. ; exit 0
#    $(call cmd,NEXT)     next ..
#
# The 'next' command would never execute because a successful gcc
# compile would be followed by exit 0 which would short-circuit
# out of the rule without completing the recipe.
#
# By conditionalizing the exit in our terse macro via:
#
#    if [ $${cmd_RC} -ne 0 ];then exit $${cmd_RC}; fi
#
# we appropriately fail out of the larger rule only if the gcc step fails:
# 
# Rule                 Rule with macro expansion
# -------------------  -------------------------------------------
# target: dep          target: dep
#    $(call cmd,GCC)      gcc .. ; CMD_RC=1;if [ 1 -ne 0 ];then exit 1;fi
#    $(call cmd,NEXT)     next ..
# ------------------------------------------------------------------------
TIME_TAG  = $(strip [$(shell $(DATE) +"%H:%M")])
Q_CMD = $($qcmd_$1)
  CMD = $(cmd_$1)

ifeq "$(ZBUILD_VERBOSE)" "1"

    # --------------------------------------------------------------------
    #  For verbose builds, we echo the raw command and stdout/stderr to
    #  the console and log file.
    #  PIPESTATUS places a dependency on bash.
    # --------------------------------------------------------------------

    cmd = @$(and $(Q_CMD),\
        (echo "  $(TIME_TAG) $(Q_CMD) " | tee -a $(ABS_BUILD_LOG)) &&) $(CMD) 2>&1 | $(TEE) -a $(ABS_BUILD_LOG) ; CMD_RC=$${PIPESTATUS[0]}; if [ $${CMD_RC} -ne 0 ];then exit $${CMD_RC}; fi

    cmd_noat = $(and $(Q_CMD),\
        (echo "  $(TIME_TAG) $(Q_CMD) " | tee -a $(ABS_BUILD_LOG)) &&) $(CMD) 2>&1 | $(TEE) -a $(ABS_BUILD_LOG) ; CMD_RC=$${PIPESTATUS[0]}; if [ $${CMD_RC} -ne 0 ];then exit $${CMD_RC}; fi

    subshellcmd = @$(and $(Q_CMD),\
        (echo "  $(TIME_TAG) $(Q_CMD) " | tee -a $(ABS_BUILD_LOG)) &&) $(CMD) 2>&1 | $(TEE) -a $(ABS_BUILD_LOG) ; CMD_RC=$${PIPESTATUS[0]}; if [ $${CMD_RC} -ne 0 ];then exit $${CMD_RC}; fi

    subshellcmd_noat = $(and $(Q_CMD),\
        (echo "  $(TIME_TAG) $(Q_CMD) " | tee -a $(ABS_BUILD_LOG)) &&) $(CMD) 2>&1 | $(TEE) -a $(ABS_BUILD_LOG) ; CMD_RC=$${PIPESTATUS[0]}; if [ $${CMD_RC} -ne 0 ];then exit $${CMD_RC}; fi

    define ECHOL
        echo "$1$(TIME_TAG) "$2 ; echo $2 >> $(ABS_BUILD_LOG)
    endef

    define echol
        echo "  $(TIME_TAG) "$1 ; echo $1 >> $(ABS_BUILD_LOG)
    endef

    define echolonly
        echo "  $(TIME_TAG) "$1 >> $(ABS_BUILD_LOG)
    endef

    define echobothl
        echo "  $(TIME_TAG) "$1 ; echo $1 | $(TEE) -a $(ABS_BUILD_LOG)
    endef
else
    
    # --------------------------------------------------------------------
    #  For quiet builds, we dump everything to a build log and present
    #  terse renditions of build commands to the console.
    #
    #  On error, display the actual command that failed plu the associated
    #  error message.
    #
    # The '3>&1 .. 2>&3' idiom redirects stderr to stdout so we can tee 
    # stderr to the build log /and/ to the console for the benefit of 
    # humans staring at the screen, wondering why their build just
    # failed and if they should rather take up interpretive dance as a 
    # career.
    # --------------------------------------------------------------------

    cmd = @$(and $(Q_CMD),\
        (echo "  $(TIME_TAG) $(Q_CMD) " | tee -a $(ABS_BUILD_LOG)) &&) echo $(CMD) 2>&1 1>> $(ABS_BUILD_LOG) ; $(CMD) 3>&1 1>>$(ABS_BUILD_LOG) 2>&3 | $(TEE) -a $(ABS_BUILD_LOG) ; CMD_RC=$${PIPESTATUS[0]}; if [ $${CMD_RC} -ne 0 ];then exit $${CMD_RC}; fi

    cmd_noat = $(and $(Q_CMD),\
        (echo "  $(TIME_TAG) $(Q_CMD) " | tee -a $(ABS_BUILD_LOG)) &&) echo $(CMD) 2>&1 1>> $(ABS_BUILD_LOG) ; $(CMD) 3>&1 1>>$(ABS_BUILD_LOG) 2>&3 | $(TEE) -a $(ABS_BUILD_LOG) ; CMD_RC=$${PIPESTATUS[0]}; if [ $${CMD_RC} -ne 0 ];then exit $${CMD_RC}; fi

    subshellcmd = @$(and $(Q_CMD),\
        (echo "  $(TIME_TAG) $(Q_CMD)  " | tee -a $(ABS_BUILD_LOG)) &&) echo '$(CMD)' 2>&1 1>> $(ABS_BUILD_LOG) ; $(CMD) 3>&1 1>>$(ABS_BUILD_LOG) 2>&3 | $(TEE) -a $(BUILD_LOG) ; CMD_RC=$${PIPESTATUS[0]}; if [ $${CMD_RC} -ne 0 ];then exit $${CMD_RC}; fi

    subshellcmd_noat = $(and $(Q_CMD),\
        (echo "  $(TIME_TAG) $(Q_CMD)  " | tee -a $(ABS_BUILD_LOG)) &&) echo '$(CMD)' 2>&1 1>> $(ABS_BUILD_LOG) ; $(CMD) 3>&1 1>>$(ABS_BUILD_LOG) 2>&3 | $(TEE) -a $(BUILD_LOG) ; CMD_RC=$${PIPESTATUS[0]}; if [ $${CMD_RC} -ne 0 ];then exit $${CMD_RC}; fi

    define ECHOL
        $(if $3, echo "$1$(TIME_TAG) "$3, echo "$1$(TIME_TAG) "$2) | $(TEE) -a $(ABS_BUILD_LOG)
    endef

    define echol
        $(if $2, echo "  $(TIME_TAG) "$2, echo "  $(TIME_TAG) "$1) | $(TEE) -a $(ABS_BUILD_LOG)
    endef

    define echolonly
        echo "  $(TIME_TAG) "$1 >> $(ABS_BUILD_LOG)
    endef

    define echobothl
        echo "  $(TIME_TAG) "$2 ; echo $1 >> $(ABS_BUILD_LOG)
    endef
endif

# Control whitespace formatting of terse output.
print = $(shell echo $1 "$2" | awk '{printf("%-15s %s\n","$1","$2")}')

# ============================================================================
# COMMAND LIBRARY
# ============================================================================

# ----------------------------------------------------------------------------
#  Build an external dependency
#  $(call cmd,BUILD,<name-or-target>,<dir-with-makefile>,<make-target>,
#  <make-args>)
quiet_cmd_BUILD = $(call print,BUILD,$2)
      cmd_BUILD = $(MAKE) -C $3 $4 $5

# ----------------------------------------------------------------------------
#  Compile a file
#  TODO Command descriptor
quiet_cmd_CC = $(call print,CC,$4)
      cmd_CC = $2 $3 $4 $5

# ----------------------------------------------------------------------------
#  Configure a build
#  $(call cmd,CFGBLD,<dir-with-configure-script>,<configure-opts>)
quiet_cmd_CFGBLD = $(call print,CONFIGURE_BUILD,$(notdir $2))
      cmd_CFGBLD = ./configure $3

# ----------------------------------------------------------------------------
#  Invoke chown on something
#  TODO Command descriptor
quiet_cmd_CHOWN = $(call print,CHOWN $2,$3:$4 $5)
      cmd_CHOWN = $(CHOWN) $2 $3:$4 $5

# ----------------------------------------------------------------------------
#  Invoke chown -h on something
#  TODO Command descriptor
quiet_cmd_CHOWN_LINK = $(call print,CHOWN_LINK,$2:$3 $4)
      cmd_CHOWN_LINK = $(CHOWN) -h $2:$3 $4

# ----------------------------------------------------------------------------
#  Copy a file
#  $(call cmd,CP,<src>,<dest>)
quiet_cmd_CP = $(call print,CP,$2 $3)
      cmd_CP = $(CP) $2 $3

# ----------------------------------------------------------------------------
#  Copy files/dirs with options
#  $(call cmd,COPY,<opts>,<src>,<dest>)
quiet_cmd_COPY = $(call print,CP,$3,$4)
      cmd_COPY = $(CP) $2 $3 $4

# ----------------------------------------------------------------------------
#  Copy a file (interactive)
#  $(call cmd,CP_interactive,<src>,<dest>)
quiet_cmd_CP_interactive = $(call print,CP,$2 $3)
          CP_interactive = $(CP) -i $2 $3

# ----------------------------------------------------------------------------
#  Retrieve a file using curl
#  $(call cmd,CURL,<target-file>,<source-file>)
quiet_cmd_CURL = $(call print,CURL,$3 -> $(dir $2))
      cmd_CURL = $(CURL) --connect-timeout 5 -fsSL -o $2 $3

# ----------------------------------------------------------------------------
#  Diff two files
quiet_cmd_DIFF = $(call print,DIFF,$3 $4)
      cmd_DIFF = $(DIFF) $2 $3 $4

# ----------------------------------------------------------------------------
#  Install a file
#  $(call cmd,INSTALL,<source-file>,<target-dir>,<perms>,<owner>,<group>)
quiet_cmd_INSTALL = $(call print,INSTALL,[m=$4 o=$5 g=$6] $3)
      cmd_INSTALL = $(INSTALL) -m $4 -o $5 -g $6 $2 $3

# ----------------------------------------------------------------------------
#  Install a directory
#  TODO Command descriptor
quiet_cmd_INSTALLDIR = $(call print,INSTALL-DIR,[m=$3 o=$4 g=$5] $2)
      cmd_INSTALLDIR = $(INSTALL) -m $3 -o $4 -g $5 -d $2

# ----------------------------------------------------------------------------
#  Link some C modules into a program
#  TODO Command descriptor
quiet_cmd_LINKC = $(call print,LINK,$6)
      cmd_LINKC = $2 $3 $4 $5 -o $6

# ----------------------------------------------------------------------------
# Alternate python install to export directory
# $(call cmd,MAKE_ALTINST,<name-or-target>,<dir-with-makefile>,<make-target>,<make-args>,<target-dir>)
quiet_cmd_MAKE_ALTINST = $(call print,$2,$3 -> $6)
      cmd_MAKE_ALTINST = $(MAKE) -C $3 $4 $5

# ----------------------------------------------------------------------------
#  TODO Command descriptor
quiet_cmd_MK_F_MANIFEST = $(call print,MANIFEST,$4)
      cmd_MK_F_MANIFEST = $(call make-file-manifest,$2,$3,$4)

define make-file-manifest
        (cd $1 && find .$2 -type f) | sed -e "s|^\.\/|\/|g" | tee $3
endef

# ----------------------------------------------------------------------------
quiet_cmd_MK_L_MANIFEST = $(call print,MANIFEST,$4)
      cmd_MK_L_MANIFEST = $(call make-link-manifest,$2,$3,$4)

define make-link-manifest
        (cd $1 && find .$2 -type l) | sed -e "s|^\.\/|\/|g" | tee $3
endef

# ----------------------------------------------------------------------------
quiet_cmd_MK_D_MANIFEST = $(call print,MANIFEST,$5)
      cmd_MK_D_MANIFEST = $(call make-dir-manifest,$2,$3,$4,$5)

define make-dir-manifest
        (cd $1 && find .$2 -depth -type d) |sed -e "s|^\.\/\/|\/|g" -e "s|^\.\/|\/|g" -e "/^\.$$/d"  -e "s|^$(3)$$||g" | tee $4
endef

# ----------------------------------------------------------------------------
#  Make deps for a C program
#  $(call cmd,MKDEPC,<source-file>,<object-file>,<depend-file>)
quiet_cmd_MKDEPC = $(call print,MKDEPC,$4)
      cmd_MKDEPC = $(call make-depend,$2,$3,$4)

# ----------------------------------------------------------------------------
#  Make library deps for a C program
#  $(call cmd,MKDEPL,<object-file>,<program-file>)
quiet_cmd_MKDEPL = $(call print,MKDEPL,$3.$(LINKDEP_EXT))
      cmd_MKDEPL = $(call make-lib-depend,$2,$3)

# ----------------------------------------------------------------------------
#  Make a directory
#  $(call cmd,MKDIR,<path>)
quiet_cmd_MKDIR = $(call print,MKDIR,$2)
      cmd_MKDIR = $(MKDIR) -p $2

# ----------------------------------------------------------------------------
#  Invoke maven <arg>
#  TODO Command descriptor
quiet_cmd_MVN    = $(call print,MVN,$2 $3)
      cmd_MVN    = $(MVN) $(JVM_OPTS) $2

quiet_cmd_MVNASM = $(call print,MVN,assemble $3)
      cmd_MVNASM = $(MVN) $(JVM_OPTS) $2

# ----------------------------------------------------------------------------
#  Move a file or directory
#
#  We use -f otherwise we make get interactive mode:
#  mv: try to overwrite ‘/etc/logrotate.d/zenoss’, overriding mode 0600 (rw-------)?
#
#  TODO Command descriptor
quiet_cmd_MV     = $(call print,MV,$2 $3)
      cmd_MV     = $(MV) -f $2 $3

# ----------------------------------------------------------------------------
#  Invoke python <arg>
#  TODO Command descriptor
quiet_cmd_PYTHON = $(call print,PYTHON,$2 $3 $4 $5 $6 $7 $8)
      cmd_PYTHON = $(PKGPYTHON) $2 $3 $4 $5 $6 $7 $8

# ----------------------------------------------------------------------------
#  Invoke python pip <arg>
#  TODO Command descriptor
quiet_cmd_PIP = $(call print,PIP,$2 $3 $4 $5)
      cmd_PIP = $(PIP) $2 $3 $4 $5

# ----------------------------------------------------------------------------
#  Invoke python easy_install <arg>
#  TODO Command descriptor
quiet_cmd_EASY_INSTALL = $(call print,EASY_INSTALL,$2 $3 $4 $5)
      cmd_EASY_INSTALL = $(EASY_INSTALL) $2 $3 $4 $5

# ----------------------------------------------------------------------------
#  Remove a file
#  $(call cmd,RM,<source-file>)
quiet_cmd_RM = $(call print,RM,$2)
      cmd_RM = $(RM) -f $2

# ----------------------------------------------------------------------------
#  Remove a directory
#  $(call cmd,RMDIR,<source-dir>)
quiet_cmd_RMDIR = $(call print,RMDIR,$2)
      cmd_RMDIR = $(RM) -rf "$2"

# ----------------------------------------------------------------------------
#  Remove a directory in a safe way
#  $(call cmd,SAFE_RMDIR,<source-directory>)
quiet_cmd_SAFE_RMDIR = $(call print,RMDIR,$2)
      cmd_SAFE_RMDIR = $(RM) -ri "$2"

# ----------------------------------------------------------------------------
#  sed
#  TODO Command descriptor
quiet_cmd_SED = $(call print,SED,$5 $4)
      cmd_SED = $(SED) $2 $3 > $4

# ----------------------------------------------------------------------------
# sed | tee filename
#
# This works better than plain $(call cmd,SED,...) with our terse builds since 
# the sed output will otherwise just dump to the build log and not to the 
# output file as desired.
quiet_cmd_SEDTEE = $(call print,SED,$3   $4)
      cmd_SEDTEE = $(SED) $2 $3 | $(TEE) $4

# ----------------------------------------------------------------------------
#  Symlink
#  $(call cmd,SYMLINK,<src>,<dest>)
LN_OPTS = -sf
quiet_cmd_SYMLINK = $(call print,SYMLINK,$3 -> $2)
      cmd_SYMLINK = $(LN) $(LN_OPTS) $2 $3

# ----------------------------------------------------------------------------
#  Create a tar.gz file. Remove suspect or empty archive on error.
#  TODO Command descriptor
quiet_cmd_TAR = $(call print,TAR,$@)
      cmd_TAR = ($(TAR) zcvf $@ -C "$2" $3) || $(RM) -f "$@"

# ----------------------------------------------------------------------------
#  Touch a file
#  $(call cmd,TOUCH,<source-file>)
quiet_cmd_TOUCH = $(call print,TOUCH,$2)
      cmd_TOUCH = $(TOUCH) $2

# ----------------------------------------------------------------------------
#  Untar something into an existing directory
#  $(call cmd,UNTAR,<src.tar>,<dest>)
quiet_cmd_UNTAR = $(call print,UNTAR,$2 -> $3)
      cmd_UNTAR = $(TAR) -xvf "$2" -C $3

#----------------------------------------------------------------------------
#  Untar something into an existing directory
#  $(call cmd,UNTGZ,<src.tgz>,<dest>)
quiet_cmd_UNTGZ = $(call print,UNTGZ,$2 -> $3)
      cmd_UNTGZ = $(TAR) -zxvf $2 -C $3

# ----------------------------------------------------------------------------
# Get the value of an xml path
# $(call cmd,XPATH,<pom-file>,<xpath>)
quiet_cmd_XPATH = $(call print,XPATH,$2 -> $3)
      cmd_XPATH = $(XPATH) -q -e $3 $2

#----------------------------------------------------------------------------
# Invoke virtualenv to install python and headers/libs
# TODO Command descriptor
quiet_cmd_VIRTUALENV = $(call print,VIRTUALENV,$3 -> $4/bin/python)
      cmd_VIRTUALENV = $(VIRTUALENV) $2 -p $3 $4

quiet_cmd_RELOCATABLE = $(call print,RELOCATABLE,$2)
      cmd_RELOCATABLE = $(VIRTUALENV) --relocatable $2

# ============================================================================
# MACRO UTILITIES
# ============================================================================

# ----------------------------------------------------------------------------
#  Configure gcc to dump out header files actually used at compile-time
# ----------------------------------------------------------------------------
GCC_MAKE_DEPENDENCY_RULES = -M
ifeq "$(INCLUDE_SYSINC_DEPS)" "yes"
    SUPPRESS_SYSINC_DEPS =
else
    # Do not include system header directories (nor header files that are
    # included directly or indirectly from such headers).  These hardly ever
    # change so making rebuilds sensitive to their modtimes is usually
    # overkill.
    SUPPRESS_SYSINC_DEPS = M
endif

# Give us control on the name of the dependency file (e.g., hello.d).
GCC_MAKE_DEP_FILENAME = -MF

# Work around errors from 'make' if a header file is removed without updating
# the makefile.
GCC_MAKE_PHONY_TARGETS = -MP

# Override target of emitted dependency rule se we can include proper pathing
# to our object directory,
GCC_MAKE_MOD_TARGET_PATH = -MT

# $(call make-depend,<source-file>,<object-file>,<depend-file>)
define make-depend
    $(GCC) $(CFLAGS) $(CPPFLAGS) $(TARGET_ARCH) $1\
        $(GCC_MAKE_DEPENDENCY_RULES)$(SUPPRESS_SYSINC_DEPS)\
        $(GCC_MAKE_PHONY_TARGETS)       \
        $(GCC_MAKE_MOD_TARGET_PATH) $2  \
        $(GCC_MAKE_DEP_FILENAME) $3
endef

# $(call make-lib-depend,object-file,program-file)
LINKDEP_EXT = dlibs
define make-lib-depend
    if $(LINK.c) $1 $(LOADLIBES) -Wl,--trace $(LDLIBS) -o $2 2>/dev/null 1>&2 ;then \
        libdep_file=$2.$(LINKDEP_EXT) ;\
        echo "$2: $1 \\" > $${libdep_file} ;\
        $(LINK.c) $1 $(LOADLIBES) -Wl,--trace $(LDLIBS) -o $2 |\
            sed -e "s|^-l[^ ]*||g" | sed -e "s|(\([^ ]*\.a\))\([^ ]*\)|\1[\2]|g" | sed -e "s|^[ ]*$$||g" | egrep -v "$1" | sed "/^[ ]*$$/d" | sed -e "s|[()]*||g" -e "s|^[ ]*||g" -e "s|.*ld: mode.*||g" | sed /^$$/d |\
        while read line ;\
        do \
                case $${line} in \
                        *..*) \
                                readlink -m $${line} ;\
                                :;;\
                        *) \
                                echo $${line} ;\
                                :;;\
                esac ;\
        done | sed -e "s|^| |g" -e "s|$$| \\\\|g" >> $${libdep_file} ;\
    fi
endef

# ---------------------------------------------------------------------------
define show-vars
        @name_values="$(foreach var,$2,$(var)=$($(var)))" ;\
        echo -e "\n$1" ;\
        echo $(LINE60) ;\
        echo "Name=Value" | sed -e "s|^_||g" -e "s|=| |g" | awk '{printf("%-25s %s\n"),$$1,$$2}'  ;\
        for name_value in $${name_values} ;\
        do \
                case "$${name_value}" in \
                        *=*) \
                                echo $(LINE60) ;\
                                echo $${name_value} | sed -e "s|^_||g" -e "s|=| |g" | awk '{printf("%-25s %s\n"),$$1,$$2}'  ;;\
                *) \
                        echo $${name_value} | awk '{printf("                          %s\n"),$$1}'  ;;\
                        esac ;\
        done ;\
        echo $(LINE60)
endef

# ============================================================================
# TARGETS
# ============================================================================

# ----------------------------------------------------------------------------
# These should probably live only at a top-level makefile so we don't clutter
# component builds with out-of-scope targets.
# ----------------------------------------------------------------------------
# zenmagic.mk: zenmagic.mk.in config.status
#	./config.status $@
#
# config.status: configure
#	./config.status --recheck
#
# distfiles = configure.ac configure zenmagic.mk.in
# target_distfiles = $(patsubst %,$(distdir)/%,$(distfiles))
#
# .PHONY: $(distdir)
# $(distdir): $(target_distfiles)
#
# $(target_distfiles): $(distdir)/% : % 
#	mkdir -p $(distdir)/src
#	cp $< $@
# ----------------------------------------------------------------------------
	
.PHONY: dflt_component_help
dflt_component_help:
	@echo
	@echo "Zenoss 5.x $(_COMPONENT) makefile"
	@echo
	@echo "Usage: make <target>"
	@echo "       make <target> V=1 # for verbose output"
	@echo
	@echo "where <target> is one or more of the following:"
	@echo $(LINE)
	@make -rpn | $(SED) -n -e '/^$$/ { n ; /^[^ ]*:/p ; }' | $(GREP) -v .PHONY| $(SORT) |\
	$(SED) -e "s|:.*||g" | $(EGREP) -v "^\.|^$(blddir)\/|install|$(prefix)|^\/|^dflt_|clean|FORCE" | $(PR) -t -w 80 -3
	@echo $(LINE)
	@make -rpn | $(SED) -n -e '/^$$/ { n ; /^[^ ]*:/p ; }' | $(GREP) -v .PHONY| $(SORT) |\
	$(SED) -e "s|:.*||g" | $(EGREP) -v "^\.|^$(blddir)\/|^$(prefix)\/|^\/|^dflt_" | $(EGREP) install | $(PR) -t -w 80 -3
	@echo $(LINE)
	@make -rpn | $(SED) -n -e '/^$$/ { n ; /^[^ ]*:/p ; }' | $(GREP) -v .PHONY| $(SORT) |\
	$(SED) -e "s|:.*||g" | $(EGREP) -v "^\.|^$(blddir)\/|^$(prefix)\/|^\/|^dflt_" | $(EGREP) clean | $(PR) -t -w 80 -3
	@echo $(LINE)
	@echo "Build results logged to $(BUILD_LOG)."
	@echo

.PHONY: dflt_devinstall
dflt_devinstall: parent_target = $(shell echo $@ | sed -e "s/dflt_//g")
dflt_devinstall:
	@echo "$(parent_target) not implemented yet. You're smart and good looking. Teach me how to do $(parent_target)?"

.PHONY: dflt_component_uninstall
dflt_component_uninstall:
	@if [ -d "$(_DESTDIR)$(prefix)" ];then \
		$(call cmd_noat,SAFE_RMDIR,$(_DESTDIR)$(prefix)) ;\
		if [ $$? -eq 0 ];then \
			$(call echol,$(LINE)) ;\
			$(call echol,"$(_COMPONENT) uninstalled from $(_DESTDIR)$(prefix)") ;\
		else \
			echo "[$@] Error unable to remove [$(_DESTDIR)$(prefix)]." ;\
			echo "[$@] Maybe you intended 'sudo make uninstall' instead? But be sure. :-)" ;\
			exit 1 ;\
		fi ;\
	fi

.PHONY: dflt_component_clean
dflt_component_clean: 
ifeq "$(REQUIRES_JDK)" "1"
	$(call cmd,MVN,clean)
else ifeq "$(REQUIRES_PYTHON)" "1"
	$(call cmd,PYTHON,setup.py,clean,--all)
endif

.PHONY: dflt_component_mrclean dflt_component_distclean
dflt_component_mrclean dflt_component_distclean: dflt_component_clean
	@for target_file in $(wildcard $(CHECKED_TOOLS_VERSION_BRAND) $(CHECKED_TOOLS) $(CHECKED_ENV)) ;\
	do \
		$(call cmd_noat,RM,$${target_file}) ;\
	done
	@if [ -f "$(ABS_BUILD_LOG)" ]; then \
		$(RM) $(ABS_BUILD_LOG) ;\
	fi
