#!/bin/bash
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

# THIS SCRIPT WILL BLOW AWAY YOUR DATABASE
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

# read configuration from global.conf
dbtype=$(${zengc} -p zodb-db-type)
host=$(${zengc} -p zodb-host)
port=$(${zengc} -p zodb-port)
user=$(${zengc} -p zodb-user)
userpass=$(${zengc} -p zodb-password)
admin=$(${zengc} -p zodb-admin-user)
adminpass=$(${zengc} -p zodb-admin-password)
dbname=$(${zengc} -p zodb-db)

# Shut down zenoss if it's running.
# Faster to check pid files than run the zenoss script.
for pidfile in $(find $ZENHOME/var -name \*.pid); do
    pid=$(cat $pidfile)
    if ps -p $pid >/dev/null; then
        echo "Stopping Zenoss"
        $ZENHOME/bin/zenoss stop
        break
    fi
done

# Drop and recreate the ZODB relstorage database
zeneventserver-create-db --dbtype $dbtype --dbhost $host --dbport $port --dbadminuser $admin --dbadminpass "${adminpass}" --dbuser $user --dbpass "${userpass}" --force --dbname $dbname --schemadir $ZENHOME/Products/ZenUtils/relstorage

# Drop and recreate the ZODB session database
zeneventserver-create-db --dbtype $dbtype --dbhost $host --dbport $port --dbadminuser $admin --dbadminpass "${adminpass}" --dbuser $user --dbpass "${userpass}" --force --dbname ${dbname}_session --schemadir $ZENHOME/Products/ZenUtils/relstorage

# Drop and recreate the ZEP event database
zeneventserver-create-db --dbtype $dbtype --dbhost $host --dbport $port --dbadminuser $admin --dbadminpass "${adminpass}" --dbuser $user --dbpass "${userpass}" --force

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

