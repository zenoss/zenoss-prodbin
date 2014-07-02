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
    fi
    return $?
}


help() {
    echo "usage:"
    echo "   zenpack help"
    echo "   zenpack install <zenpack_egg_relpath>"
    echo "   zenpack list"
    echo "   zenpack uninstall <zenpack_name>"
    return 1
}


install() {
    # Map host path to container path
    hostZenpackPath=$1
    shift
    if [[ "${hostZenpackPath:0:1}" = "/" ]]; then
        containerZenpackPath=$hostZenpackPath
    else
        containerZenpackPath="/mnt/pwd/"$hostZenpackPath
    fi

    #Test for presence of ZenPack egg
    if [[ ! -r "$containerZenpackPath" ]]; then
        echo "Unable to read ZenPack file: '$hostZenpackPath'"
        echo "The ZenPack must be located in the current working directory and must be specified with a relative path."
        return 1
    fi

    zenpack --install "$containerZenpackPath" "$@"
    return $?
}


uninstall() {
    zenpack --uninstall "$@"
    return $?
}


list() {
    zenpack --list "$@"
    return 1
}

