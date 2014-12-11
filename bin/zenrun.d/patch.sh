#! /usr/bin/env bash   
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

applyPatches() {
    
    # No need to subshell here for 'cd' because this whole process needs to 
    # happen in $ZENHOME
    cd $ZENHOME
    if ! which quilt > /dev/null 2>&1; then
       echo "Unable to apply custom patches - quilt is not installed" 
       return 1
    fi
    
    # First pop everything off (the image may or may not actually have the
    # patches applied, so need to pop them first)
    quilt pop -a
    RC=$?
    if [[ $RC != 0 ]]; then
        echo "Error popping off patches!"
        return "$?"
    fi
    
    quilt push -a
    RC=$?
    if [[ $RC != 0 ]]; then
        failed_changeset=`quilt next`
        echo "Error patching your system.  Failed on changeset: ${failed_changeset}"
        return "$RC"
    fi

    return 0
}

