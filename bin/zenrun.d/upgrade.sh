#! /usr/bin/env bash   
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


runCustomUpgradeScripts() {
    . $ZENHOME/bin/zenfunctions
    $PYTHON ./upgrade_scripts/update_zep_schema.py
}

doUpgrade() {
    zenpack --restore || return "$?"
    zenmigrate || return "$?"
    runCustomUpgradeScripts || return "$?"
    return 0
}

