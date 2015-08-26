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
    # Move service-id argument from beginning to end of argument list.  This
    # allows us to use the next argument as the subcommand.
    serviceid=$1
    shift
    if [[ $# -eq 0 ]]; then
        echo missing zenpack subcommand
        help
        return 1
    fi
    set -- "$@" $serviceid

    if declare -f $1 &> /dev/null; then
        "$@"
    else
        echo unknown zenpack sub-command: \"$1\"
        help
        return 1
    fi
    return $?
}


help() {
    echo "usage:"
    echo "   zenpack help"
    echo "   zenpack list"
    return 1
}


list() {
    zenpack --list "$@"
    return $?
}

