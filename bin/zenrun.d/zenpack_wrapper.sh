#! /usr/bin/env bash   
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

# wrapper for zenpack command, allowing the command to run in zenrun
__DEFAULT__() {
    zenpack $*
    if test $? -eq 0; then
        return 42
    fi
    return 0
 }
