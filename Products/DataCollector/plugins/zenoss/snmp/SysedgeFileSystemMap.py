###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__="""SysedgeFileSystemMap

SysedgeFileSystemMap maps the interface and ip tables to interface objects

$Id: SysedgeFileSystemMap.py,v 1.11 2004/04/07 16:26:53 edahl Exp $"""

__version__ = '$Revision: 1.11 $'[11:-2]

import re

from CollectorPlugin import SnmpPlugin

class SysedgeFileSystemMap(SnmpPlugin):

    remoteClass = "Products.ZenModel.FileSystem"
    relationshipName = "filesystems"
    componentName = "os"

    fsTableOid = '.1.3.6.1.4.1.546.1.1.1.7.1'
    fsMap = {
            '.1': 'snmpindex',
             '.2': 'storageDevice',
             '.3': 'mount',
             '.10': 'type',
             '.4': 'blockSize',
             '.5': 'totalBlocks',
             '.6': 'freeBlocks',
             '.7': 'totalFiles',
             '.8': 'availFiles',
             '.9': 'maxNameLen',
             '.14': 'capacity',
             '.15': 'inodeCapacity',
             }


    def condition(self, device, log):
        """does device meet the proper conditions for this collector to run"""
        return False



    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('Collecting Sysedge filesystem for device %s' % device.id)
        fstable = snmpsess.collectSnmpTableMap(self.fsTableOid, self.fsMap)
        #fstable = snmpsess.snmpTableMap(fstable, self.fsMap)
        dontcollectfstypes = getattr(device, 'zFileSystemMapIgnoreTypes', ())
        dontcollectfsnames = getattr(device, 'zFileSystemMapIgnoreNames', None)
        datamaps = []
        for fs in fstable.values():
            if (fs['type'] in dontcollectfstypes or 
                (dontcollectfsnames 
                and re.search(dontcollectfsnames, fs['mount']))):
                continue
            bsize = long(fs['blockSize'])
            fs['title'] = fs['mount']
            fs['id'] = self.prepId(fs['mount'], '-')
            fs['totalBytes'] = bsize * fs['totalBlocks']
            fs['availBytes'] = bsize * fs['freeBlocks']
            fs['usedBytes'] = fs['totalBytes'] - fs['availBytes']
            del fs['totalBlocks']
            del fs['freeBlocks']
            datamaps.append(fs)
        return datamaps


