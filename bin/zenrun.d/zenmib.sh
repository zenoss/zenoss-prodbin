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
    cd /mnt/pwd
    zenmib "$@"
    return $?
}

help() {
    echo "usage:"
    echo "   zenmib help"
    echo "   zenmib run [--nocommit] <zenmib_file_url>"
    return 0
}


