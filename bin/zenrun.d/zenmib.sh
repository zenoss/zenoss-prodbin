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
    # The first argument is the subcommand.
    if [[ $# -eq 0 ]]; then
        echo missing zenmib subcommand
        help
        return 1
    fi
    set -- "$@"

    if declare -f $1 &> /dev/null; then
        "$@"
    else
        echo unknown zenmib sub-command: \"$1\"
        help
    fi
    return $?
}


help() {
    echo "usage:"
    echo "   zenmib help"
    echo "   zenmib run <zenmib_file_url>"
    return 1
}


run() {
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


