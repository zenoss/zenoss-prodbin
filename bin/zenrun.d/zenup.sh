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

mapPath() {
    local hostArtifactPath=$1
    local __resultvar=$2

    if [[ "${hostArtifactPath:0:1}" = "/" ]]; then
        local containerArtifactPath=$hostArtifactath
    else
        local containerArtifactPath="/mnt/pwd/"$hostArtifactPath
    fi

    #Test for presence of artifact
    if [[ ! -r "$containerArtifactPath" ]]; then
        echo "Unable to read file: '$hostArtifactPath'"
        echo "The specified file must be located in the current working directory and must be specified with a relative path."
        exit 1
    fi

    eval $__resultvar="$containerArtifactPath"
}

install() {
    mapPath ${!#} artifactPath
    set -- "${@:1:$(($#-1))}" "$artifactPath"
    zenup install "$@"
    return $?
}

init() {
    mapPath ${!#} artifactPath
    set -- "${@:1:$(($#-1))}" "$artifactPath"
    zenup init "$@"
    return $?
}

patch() {
    mapPath ${!#} artifactPath
    set -- "${@:1:$(($#-1))}" "$artifactPath"
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

