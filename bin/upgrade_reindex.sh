#!/bin/bash
#
# Only force a reindex if we're upgrading from < 6.x. The upgrade script provides the top level service name as an argument.
#

# Get the major version number that we're upgrading from.
MAJOR=$(cat /var/zenoss/upgrade_from_version.txt | cut -d"." -f1)
TOPSERVICE=$@

# Resmgr/Core upgraded to Solr in version 6.0.0.  UCSPM will probably upgrade to Solr in 3.x
if [[ "${TOPSERVICE}" == "ucspm" ]]; then
  SOLRVERSION=3
else
  SOLRVERSION=6
fi

# Only force a catalog reindex if the current major version of RM is less than 6.
if [[ $MAJOR -lt $SOLRVERSION ]]; then
    /opt/zenoss/bin/zencatalog run --createcatalog --forceindex
else
    echo "Upgrading from ${TOPSERVICE} major version ${MAJOR}. Skipping catalog reindex."
fi
