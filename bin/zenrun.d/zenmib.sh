#! /usr/bin/env bash   
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__DEFAULT__() {
    local nocommit=0
    if echo "$@" | egrep -- '--nocommit|--keeppythoncode'; then
        nocommit=1
    fi

    zenmib "$@"
    status=$?
    if [[ 1 = "$nocommit" ]]; then
        return 1
    else
        return $status
    fi
}


help() {
    echo "usage:"
    echo "   zenmib help"
    echo "   zenmib run [--nocommit] <zenmib_file_url>"
    return 1
}


