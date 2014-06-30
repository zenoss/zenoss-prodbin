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
    args=$($RUNPATH/util/replaceZenpackPath.py "$@")
    status=$?
    if test $status -ne 0 ; then
        return $status
    fi
    IFS=$(printf "\x01") read -ra args <<< "$args"
    zenpack "${args[@]}"
    return $?
 }
