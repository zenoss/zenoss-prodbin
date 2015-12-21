#! /usr/bin/env bash   
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

doUpgrade() {
    SERVICE_MIGRATION_PATH=`python /opt/zenoss/bin/service-migrate.py begin` || return "$?"
    export MIGRATE_INPUTFILE=$SERVICE_MIGRATION_PATH
    export MIGRATE_OUTPUTFILE=$SERVICE_MIGRATION_PATH
    zenpack --restore || return "$?"
    zenmigrate || return "$?"
    unset MIGRATE_INPUTFILE
    unset MIGRATE_OUTPUTFILE
    python /opt/zenoss/bin/service-migrate.py end || return "$?"
    zengc=$ZENHOME/bin/zenglobalconf
    dbtype=$(${zengc} -p zodb-db-type)
    host=$(${zengc} -p zodb-host)
    port=$(${zengc} -p zodb-port)
    user=$(${zengc} -p zodb-user)
    userpass=$(${zengc} -p zodb-password)
    # TODO: zodb upgrade path
    /opt/zenoss/bin/zeneventserver-create-db \
        --dbtype $dbtype --dbhost $host --dbport $port \
        --dbuser $user --dbpass "${userpass}" \
        --update_schema_only || return "$?"
    return 0
}

