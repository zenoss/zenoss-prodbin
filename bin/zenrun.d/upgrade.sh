#! /usr/bin/env bash   
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

doUpgrade() {
    zenpack --restore || return "$?"
    zenmigrate || return "$?"
    return 0
}

