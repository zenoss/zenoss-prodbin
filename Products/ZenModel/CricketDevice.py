#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""CricketDevice

Mixin to provide cricket configuration generation for devices

$Id: CricketDevice.py,v 1.21 2004/04/06 22:33:23 edahl Exp $"""

__version__ = "$Revision: 1.21 $"[11:-2]


import re
import logging

from Products.ZenRRD.utils import RRDObjectNotFound
from Products.ZenRRD.RRDTargetType import lookupTargetType

from Exceptions import ZenModelError

class RelationNotFound(ZenModelError): pass

class CricketDevice:
    """
    CricketDevice generates cricket configurations from the ZenRRD setup.
    CricketBuilder calls cricketGenerate to perform this function.
    cricketGenerate returns the following data structure:
    [['targetpath', {'targettype1':['ds1','ds2',...],'targetype2':['ds3'...]},
        [
        {'target':'targetnmae','inst':1,'monitor-thresholds':'crkthreshold'},
        ...
        ]
     ['targetpath',[moretargetdicts...]]
    ] 
    """

    def cricketGenerate(self):
        """generate the cricket config data structure for this device"""
        cd = []
        self.addTargetData(cd, self.cricketDevice())
        self.addTargetData(cd, self.cricketInterfaces())
        self.addTargetData(cd, self.cricketFilesystems())
        self.addTargetData(cd, self.cricketDisks())
        self.setLastCricketGenerate()
        return cd


    def addTargetData(self, cricketData, targetinfo):
        if not targetinfo: return
        targetpath, targettypes, targets = targetinfo
        targets = list(targets)
        targets.insert(0,self.cricketTargetDefault())
        cricketData.append((targetpath, targettypes, targets))


    def setCricketThresholds(self, context, targets):
        """add thresholds for an object using its target type"""
        for targetdata in targets:
            self.setCricketThreshold(context, targetdata)
        return targets


    def setCricketThreshold(self, context, targetdata):
        targettype = lookupTargetType(context, targetdata['target-type'])
        thresholds = targettype.getCricketThresholds(context)
        if thresholds:
            targetdata['monitor-thresholds'] = thresholds
    

    def cricketTargetDefault(self):
        """build target default information 
        used by cricket to connect to target"""
        if not (hasattr(self, '_v_targetdefault')
            and self._v_targetdefault['snmp-host'] == self.id):
            self._v_targetdefault = {}
            self._v_targetdefault['target'] = '--default--' 
            self._v_targetdefault['snmp-host'] = self.id
            self._v_targetdefault['snmp-community'] = self.zSnmpCommunity
            self._v_targetdefault['snmp-port'] = self.zSnmpPort
            if self.snmpOid.find('.1.3.6.1.4.1.9') > -1:
                self._v_targetdefault['snmp-version'] = '2c'
        return self._v_targetdefault
 
 
    def cricketDevice(self):
        """build the targets for the device itself
        use cricketTargetPath to """
        targetpath = self.cricketTargetPath()
        targettypes = {}
        targets = self.callscript(self, 'scCricketDevice')
        if not targets:
            targetdata = {}
            targetdata['target'] = self.id
            crtype = self.cricketDeviceType()
            if not crtype: return
            targetdata['target-type'] = crtype
            targets = (targetdata,)
        for target in targets:
            ttype = lookupTargetType(self, target['target-type'])
            targettypes[ttype.getName()] = ttype.dsnames
        targets = self.setCricketThresholds(self, targets)
        self.setCricketTargetMap(targetpath, targets) 
        return (targetpath, targettypes, targets)
 

    def cricketDeviceType(self):
        """default method for getting device type
        first looks for scCricketDeviceType function that would
        calculate the type if that is not found
        it looks for zCricketDeviceType attribute
        default value is 'Device'"""
        deviceType = self.callscript(self, 'scCricketDeviceType')
        if not deviceType:
            deviceType = getattr(self, 'zCricketDeviceType', "Device")
        try:
            lookupTargetType(self, deviceType)
        except RRDObjectNotFound:
            logging.warn(
                "RRDTargetType %s for device not found", deviceType)
        return deviceType


    def cricketInterfaces(self):
        """build the targets for device interfaces"""
        targetpath = self.cricketTargetPath() + '/interfaces'
        targettypes = {}
        targets = []
        for interface in self.os.interfaces.objectValuesAll():
            if not interface.adminStatus == 1: continue
            self.interfaceMultiTargets(interface, targetpath)
            inttype = self.cricketInterfaceType(interface)
            if not inttype: continue
            ttype = lookupTargetType(self, inttype)
            targettypes[ttype.getName()] = ttype.dsnames
            targetdata = {}
            targetdata['target'] = interface.id
            targetdata['target-type'] = inttype
            targetdata['inst'] = interface.ifindex
            targetdata['display-name'] = interface.name
            targetdata['short-desc'] = interface.description 
            self.setCricketThreshold(interface, targetdata)
            interface.setCricketTargetMap(targetpath, targetdata)
            targets.append(targetdata)
        return (targetpath, targettypes, targets)
 

    def cricketFilesystems(self):
        """build the cricket configuration for filesystem monitoring"""
        targetpath = self.cricketTargetPath() + '/filesystems'
        targettypes = {}
        targets = []
        cricketFilesystemType = getattr(self, "zCricketFilesystemType", 
                                                "Filesystem")
        try:
            ttype = lookupTargetType(self, cricketFilesystemType)
            targettypes[ttype.getName()] = ttype.dsnames
            for fs in self.os.filesystems.objectValuesAll():
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
            logging.warn("RRDTargetType %s for filesystem not found",
                            cricketFilesystemType)
        return (targetpath, targettypes, targets)


    def cricketDisks(self):
        targetpath = self.cricketTargetPath() + '/disks'
        targettypes = {}
        targets = []
        cricketDiskType = getattr(self, "zCricketHardDiskType", 
                                                "HardDisk")
        try:
            ttype = lookupTargetType(self, cricketDiskType)
            targettypes[ttype.getName()] = ttype.dsnames
            for disk in self.hw.harddisks():
                targetdata = {}
                targetdata['target'] = disk.id
                targetdata['target-type'] = cricketDiskType
                targetdata['display-name'] = disk.description
                targetdata['inst'] = disk.snmpindex
                self.setCricketThreshold(disk, targetdata)
                disk.setCricketTargetMap(targetpath, targetdata)
                targets.append(targetdata)
        except RRDObjectNotFound:
            logging.warn("RRDTargetType %s for harddisk not found", 
                            cricketDiskType)
        return (targetpath, targettypes, targets)


    def interfaceMultiTargets(self, interface, targetpath):
        """setup graphs that have multiple targets with 
        different potentially types in one graph"""
        from Products.ZenRRD.RRDMGraph import RRDMGraph
        mtargets = []
        if interface.type == 'CATV MAC Layer':
            interface.clearCricketMGraph()
            sufixes = ("-downstream", "-upstream0", 
                    "-upstream1", "-upstream2", "-upstream3")
            for sufix in sufixes:
                target = targetpath + "/" + interface.id.lower() + sufix
                if target.find('down') > -1:
                    targettype = 'DownstreamInterface'
                else:
                    targettype = 'UpstreamInterface'
                mtargets.append((target, targettype))
            mg = RRDMGraph(mtargets, ("IfOctets", "IfUcastPackets", "IfErrors"))
            interface.addCricketMGraph(mg) 


    def cricketInterfaceType(self, interface):
        """determin the cricket interface type of a device
        can use a user defined map zCricketInterfaceMap
        as well as a user defined rule scCricketInterfaceMap
        """

        defaultmap = {
                    'sonet':'SRPInterface',
                    'CATV Downstream Interface': 'DownstreamInterface',
                    'CATV Upstream Interface': 'UpstreamInterface',
                    }

        defaultIgnoreTypes = ('Other', 'softwareLoopback', 'CATV MAC Layer')

        type = self.callscript(self, 'scCricketInterfaceType', interface)
        if type: return type
        intarray = getattr(self, 'zCricketInterfaceMap', None)
        if intarray:
            intmap = {}
            for im in intarray:
                ar = im.split(':') 
                if len(ar) == 2:
                    intmap[ar[0]] = ar[1]
        else:
            intmap = defaultmap
        cricketType = 'StandardInterface'
        if (self.hw.getManufacturerName() == 'Cisco' 
            and interface.speed >= 100000000):
            cricketType = 'FastInterface'

        ignoreTypes = getattr(self, 'zCricketInterfaceIgnoreTypes', None)
        if not ignoreTypes: ignoreTypes = defaultIgnoreTypes
        intType = interface.type
        if intType in ignoreTypes: 
            return None

        dontSendIntNames = getattr(self, 'zCricketInterfaceIgnoreNames', None)
        if dontSendIntNames and re.search(dontSendIntNames,interface.name):
            return None

        if intmap.has_key(intType): 
            cricketType = intmap[intType]

        if interface.type == 'sonet' and interface.name.find('POS') == 0:
            cricketType = 'FastInterface'

        return cricketType
       

    def cricketTargetPath(self):
        """get the cricket target path using DeviceClass path of the box"""
        return self.getDeviceClassPath() + '/' + self.id
    

    def callscript(self, obj, name, *args, **kargs):
        script = getattr(obj, name, None)
        if script: 
            return apply(script, args, kargs)


    def getRelatedCricketObjs(self, relation):
        """get a list of related objects that have cricket information"""
        relobj = getattr(self, relation, None)
        if relobj:
            cricketObjs = filter(lambda x: x.checkCricketData(), 
                        relobj.objectValuesAll())
            return cricketObjs
        raise RelationNotFound, "Relation %s no found on obj %s" % (
                                                relation, self.getId())

