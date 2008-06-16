#!/bin/bash
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

#
# If no configuration file exists, create a sample one.
#

. $ZENHOME/bin/zenfunctions

cd daemons
for daemonctl in * ; do
     PRGNAME=`awk -F= '/^PRGNAME=/ { print $2; }' $daemonctl | sed -e 's/\.py//' | tail -1`

     #echo "PRGNAME $PRGNAME"

     #
     # Expand any variables used to define the config file
     #
     eval CFGFILE=`awk -F= '/^CFGFILE=/ { print $2; }' $daemonctl | tail -1`
     #echo "CFGFILE $CFGFILE"

     #
     # Some sanity checks...
     #
     if [ -z "$CFGFILE" ] ; then
         echo "No configuration file for $PRGNAME found"
         continue

     elif [ $CFGFILE == '/dev/null' ] ; then
         echo "No configuration file for $PRGNAME"
         continue
     fi

     #
     # Don't overwrite possibly user-customized files!
     #
     if [ ! -f $CFGFILE ] ; then
        $PRGNAME genconf
        if [ "$?" -eq "0" ]; then
            echo "Creating configuration file for $PRGNAME..."
            `$PRGNAME genconf > $CFGFILE`
        fi
     fi
done

#
# Don't cause troubles if one of the above steps had issues.
#
exit 0
