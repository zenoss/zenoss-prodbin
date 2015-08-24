#!/bin/bash
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


help() {
    echo "usage:"
    echo "   mysql help"
    echo "   mysql rebuild_zodb_session"
    return 0
}

rebuild_zodb_session() {
    local db="zodb_session"
    echo -e "rebuilding $db - drop then create $db..."
    mysql -u root -e "drop database if exists $db; create database $db; show databases like '$db';" zodb
    rc=$?
    if [[ $rc != 0 ]]; then
        echo "FAILURE rebuilding $db"
        exit $rc
    fi
    echo "SUCCESS rebuilding $db"
    exit 0
}

