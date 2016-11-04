#!/bin/bash
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

# THIS SCRIPT WILL BLOW AWAY YOUR DATABASE.  RUN THIS IN THE
#  MARIADB CONTAINER AND THEN RUN zenreload.sh IN ZOPE or devshell
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

# Drop and recreate the ZODB relstorage database
zeneventserver-create-db --dbtype $dbtype --dbhost $host --dbport $port --dbadminuser $admin --dbadminpass "${adminpass}" --dbuser $user --dbpass "${userpass}" --force --dbname $dbname --schemadir $ZENHOME/Products/ZenUtils/relstorage

# Drop and recreate the ZODB session database
zeneventserver-create-db --dbtype $dbtype --dbhost $host --dbport $port --dbadminuser $admin --dbadminpass "${adminpass}" --dbuser $user --dbpass "${userpass}" --force --dbname ${dbname}_session --schemadir $ZENHOME/Products/ZenUtils/relstorage

# Drop and recreate the ZEP event database
zeneventserver-create-db --dbtype $dbtype --dbhost $host --dbport $port --dbadminuser $admin --dbadminpass "${adminpass}" --dbuser $user --dbpass "${userpass}" --force

