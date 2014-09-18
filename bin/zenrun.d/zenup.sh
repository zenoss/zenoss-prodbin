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
    cd "$ZENUP_PWDPATH"
    zenup install "$@"
    return $?
}

init() {
    cd "$ZENUP_PWDPATH"
    zenup init "$@"
    return $?
}

patch() {
    cd "$ZENUP_PWDPATH"
    zenup patch "$@"
    return $?
}

delete() {
    cd "$ZENUP_PWDPATH"
    zenup delete "$@"
    return $?
}

revert() {
    cd "$ZENUP_PWDPATH"
    zenup revert "$@"
    return $?
}

