#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""CricketDevice

Mixin to provide cricket configuration generation for Servers
Adds filesystem generation and device type function

$Id: CricketServer.py,v 1.8 2004/04/06 22:33:23 edahl Exp $"""

__version__ = "$Revision: 1.8 $"[11:-2]


import re

from zLOG import LOG, WARNING

from Products.ZenRRD.utils import RRDObjectNotFound
from Products.ZenRRD.RRDTargetType import lookupTargetType

from Device import Device

class CricketServer:


    def cricketGenerate(self):
        """build the cricket config for the entire device"""
        cd = Device.cricketGenerate(self, force)
        if cd:
            self.addTargetData(cd, self.cricketFilesystems())
            self.addTargetData(cd, self.cricketDisks())
        return cd
      

    def cricketFilesystems(self):
        """build the cricket configuration for filesystem monitoring"""
        objpaq = self.primaryAq()
        targetpath = objpaq.cricketTargetPath() + '/filesystems'
        targets = []
        cricketFilesystemType = getattr(objpaq, "zCricketFilesystemType", 
                                                "Filesystem")
        try:
            lookupTargetType(objpaq, cricketFilesystemType)
            for fs in objpaq.filesystems.objectValuesAll():
                targetdata = {}
                targetdata['target'] = fs.id
                targetdata['target-type'] = cricketFilesystemType
                targetdata['display-name'] = fs.mount
                targetdata['filesystem-mount'] = fs.mount
                targetdata['inst'] = fs.snmpindex
                self.setCricketThreshold(fs, targetdata)
                fs.setCricketTargetMap(targetpath, targetdata)
                targets.append(targetdata)
        except RRDObjectNotFound:
            LOG("CricketBuilder", WARNING, 
                "RRDTargetType %s for filesystem not found" 
                % cricketFilesystemType)
        return (targetpath, targets)


    def cricketDisks(self):
        objpaq = self.primaryAq()
        targetpath = objpaq.cricketTargetPath() + '/disks'
        targets = []
        cricketDiskType = getattr(objpaq, "zCricketHardDiskType", 
                                                "HardDisk")
        try:
            lookupTargetType(objpaq, cricketDiskType)
            for disk in objpaq.harddisks():
                targetdata = {}
                targetdata['target'] = disk.id
                targetdata['target-type'] = cricketDiskType
                targetdata['display-name'] = disk.description
                targetdata['inst'] = disk.snmpindex
                self.setCricketThreshold(disk, targetdata)
                disk.setCricketTargetMap(targetpath, targetdata)
                targets.append(targetdata)
        except RRDObjectNotFound:
            LOG("CricketBuilder", WARNING, 
                "RRDTargetType %s for harddisk not found" % cricketDiskType)
        return (targetpath, targets)
