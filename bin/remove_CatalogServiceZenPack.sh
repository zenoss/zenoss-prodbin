#!/bin/bash

echo "Removing Catalog Service"
CATALOG_SERVICE_EGG=`find /opt/zenoss/.ZenPacks/ -name ZenPacks.zenoss.CatalogService* | head -n 1`
if [[ -z "$CATALOG_SERVICE_EGG" ]]; then
  echo "Catalog Service egg not found.  Exiting removal script."
  exit
fi

echo "Found Catalog Service egg at $CATALOG_SERVICE_EGG"
/opt/zenoss/bin/zenpack --files-only --install $CATALOG_SERVICE_EGG
/opt/zenoss/bin/zenpack --remove ZenPacks.zenoss.CatalogService
echo "Successfully removed Catalog Service"
