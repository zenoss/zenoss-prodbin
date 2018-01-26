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
    echo "To remove the CatalogService ZenPack:"
    echo -e "1. Ensure the following services are running:\n\t * Zenoss.resmgr/Infrastructure/mariadb-model\n\t * Zenoss.resmgr/Infrastructure/mariadb-events\n\t * Zenoss.resmgr/Infrastructure/RabbitMQ\n\t * Zenoss.resmgr/Zenoss/Events/zeneventserver\n\t * Zenoss.resmgr/Infrastructure/redis\n\t * Zenoss.resmgr/Infrastructure/memcached"
    echo -e "2. Ensure the following service has stopped:\n\t *Zenoss.resmgr/Infrastructure/zencatalogservice"
    echo -e "3. Log onto the host of the Control Center master and run the following command:\n\t serviced service run zope zenpack-manager uninstall ZenPacks.zenoss.CatalogService"
    exit $status
fi
rm $tmp_output
echo "Successfully removed Catalog Service"

