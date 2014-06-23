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
    zenup "$@"
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

status() {
    __nocommit__ status "$@"
    return $?
}

info() {
    __nocommit__ info "$@"
    return $?
}

diff() {
    __nocommit__ diff "$@"
    return $?
}