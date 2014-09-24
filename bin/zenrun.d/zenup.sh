#! /usr/bin/env bash                                                                                                                       
############################################################################## 
#                                                                              
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.                        
#                                                                              
# This content is made available according to terms specified in               
# License.zenoss under the directory where your Zenoss product is installed.   
#                                                                              
##############################################################################

ZENUP_PWDPATH=/mnt/pwd
ZENUP_COMMITFILE=/tmp/zenup-successful-$(date +%Y-%m-%d.%H:%M:%S)

_setUp() {
    export ZENUPCOMMITFILELOC="$ZENUP_COMMITFILE"
}

_handleExit() {
    if [[ $1 != 0 ]]; then
        # This is to preserve the status code should it be non-0
        return $1
    elif [[ $1 == 0 && ! -f "$ZENUP_COMMITFILE" ]]; then
        return 1
    else
        return $1
    fi
}

__DEFAULT__() {
    __nocommit__ "$@"
    return $?
}

__nocommit__() {
    cd "$ZENUP_PWDPATH"
    zenup "$@"
    status=$?
    if [[ $status != 0 ]]; then 
        return $status
    fi
    return 1
}

install() {
    _setUp
    cd "$ZENUP_PWDPATH"
    zenup install "$@"
    return $(_handleExit "$?")
}

init() {
    _setUp
    cd "$ZENUP_PWDPATH"
    zenup init "$@"
    return $(_handleExit "$?")
}

patch() {
    _setUp
    cd "$ZENUP_PWDPATH"
    zenup patch "$@"
    return $(_handleExit "$?")
}

delete() {
    _setUp
    cd "$ZENUP_PWDPATH"
    zenup delete "$@"
    return $(_handleExit "$?")
}

revert() {
    _setUp
    cd "$ZENUP_PWDPATH"
    zenup revert "$@"
    return $(_handleExit "$?")
}

