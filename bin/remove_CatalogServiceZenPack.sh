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
if [[ ! $? -eq 0 ]]; then
    echo "Couldn't remove CatalogService zenpack"
    cat $tmp_output
    rm $tmp_output
    exit
fi
rm $tmp_output
echo "Successfully removed Catalog Service"
