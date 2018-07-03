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
    local RC

    cd $ZENHOME
    which quilt > /dev/null 2>&1; RC=${PIPESTATUS[0]}
    if [[ $RC != 0 ]]; then
       echo "Unable to apply custom patches - quilt is not installed" 
       return 1
    fi
    
    # Run 'quilt upgrade' to make sure things are up to date
    quilt upgrade > /dev/null 2>&1; RC=${PIPESTATUS[0]}
    if [[ $RC != 0 ]]; then
        echo "Failed to run 'quilt upgrade', exiting"
        return "$RC"
    fi

    # Assure that patch directory and series file exist.
    if [[ ! -d patches ]]; then
        mkdir patches
    fi
    touch patches/series

    # Check for new patches
    quilt unapplied > /dev/null 2>&1; RC=${PIPESTATUS[0]}
    if [[ $RC != 0 ]]; then
        echo "No patches to apply. Add/import patches first."
        return "$RC"
    fi

    # Pop off old patches, if any
    quilt top > /dev/null 2>&1; RC=${PIPESTATUS[0]}
    if [[ $RC == 0 ]]; then
        quilt pop -a
        RC=$?
        if [[ $RC != 0 ]];then
            echo "Error popping off patches!"
            return "$RC"
        fi
    fi

    # Replay all patches, including new ones
    if ! quilt push -a; then
        failed_changeset=`quilt next`
        echo "Error patching your system.  Failed on changeset: ${failed_changeset}"
        return "$RC"
    fi

    return 0
}
