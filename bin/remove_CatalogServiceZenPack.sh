#!/bin/bash

echo "Removing Catalog Service"
CATALOG_SERVICE_EGG=`find /opt/zenoss/.ZenPacks/ -name ZenPacks.zenoss.CatalogService* | head -n 1`
if [[ -z "$CATALOG_SERVICE_EGG" ]]; then
  echo "Catalog Service egg not found.  Exiting removal script."
  exit
fi

echo "Found Catalog Service egg at $CATALOG_SERVICE_EGG"
/opt/zenoss/bin/zenpack --files-only --install $CATALOG_SERVICE_EGG
#show log only if something goes wrong
tmp_output="/tmp/"`cat /dev/urandom | tr -cd 'a-f0-9' | head -c 32`
/opt/zenoss/bin/zenpack --remove ZenPacks.zenoss.CatalogService  > $tmp_output 2>&1
status=$?
if [[ ! $status -eq 0 ]]; then
    cat $tmp_output
    rm $tmp_output
    echo "Couldn't remove CatalogService zenpack"
    echo "You should remove CatalogService zenpack manually before starting the upgrade"
    echo "Make sure you have Zenoss.resmgr/Infrastructure/mariadb-model, Zenoss.resmgr/Infrastructure/mariadb-events, Zenoss.resmgr/Infrastructure/RabbitMQ, Zenoss.resmgr/Zenoss/Events/zeneventserver, Zenoss.resmgr/Infrastructure/redis, Zenoss.resmgr/Infrastructure/memcached services running and Zenoss.resmgr/Infrastructure/zencatalogservice stoped, and then from your master host run command:"
    echo "serviced service run zope zenpack-manager uninstall ZenPacks.zenoss.CatalogService"
    exit $status
fi
rm $tmp_output
echo "Successfully removed Catalog Service"

