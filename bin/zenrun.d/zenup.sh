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
    __nocommit__ "$@"
    return $?
}

__nocommit__() {
    zenup "$@"
    status=$?
    if [[ $status != 0 ]]; then 
        return $status
    fi
    return 1
}

install() {
    zenup install "$@"
    return $?
}

init() {
    zenup init "$@"
    return $?
}

patch() {
    zenup patch "$@"
    return $?
}

delete() {
    zenup delete "$@"
    return $?
}

revert() {
    zenup revert "$@"
    return $?
}
