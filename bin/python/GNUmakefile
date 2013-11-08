#============================================================================
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
#============================================================================
.DEFAULT_GOAL := help # build|clean|distclean|devinstall|install|help

with_virtualenv ?= yes

ifeq "$(with_virtualenv)" "yes"
    include virtualenv.mk
else
    include src.mk
endif
