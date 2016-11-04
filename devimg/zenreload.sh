#!/bin/bash
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

# THIS SCRIPT SHOULD BE RUN ON A CLEAN DATABASE
# IT WILL BLOW AWAY ALL ZENPACKS AND THEN RELOAD THE BASE DATABASES
# Use --xml option to this script to rebuild using DmdBuilder and the XML files
# Default is simply to reload from SQL dump

if [ -z "${ZENHOME}" ]; then
    if [ -d /opt/zenoss ] ; then
        ZENHOME=/opt/zenoss
    else
        echo "Please define the ZENHOME environment variable"
        exit 1
    fi
fi

zengc=$ZENHOME/bin/zenglobalconf

echo "Deleting Zenpacks"
rm -rf $ZENHOME/ZenPacks/*

if [ -d $ZENHOME/var/catalogservice ]; then
    rm -rf $ZENHOME/var/catalogservice
fi

# Creates the initial user file for zenbuild
python -m Zope2.utilities.zpasswd -u admin -p zenoss $ZENHOME/inituser
zenbuild -v 10 -u$admin -p "$adminpass" "$@"
# truncate daemons.txt file
cp /dev/null $ZENHOME/etc/daemons.txt