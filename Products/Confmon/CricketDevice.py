#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""CricketDevice

Mixin to provide cricket configuration generation for devices

$Id: CricketDevice.py,v 1.21 2004/04/06 22:33:23 edahl Exp $"""

__version__ = "$Revision: 1.21 $"[11:-2]


import re

from zLOG import LOG, WARNING

from Products.RRDProduct.utils import RRDObjectNotFound
from Products.RRDProduct.RRDTargetType import lookupTargetType

class RelationNotFound(Exception): pass

class CricketDevice:

    def cricketGenerate(self):
        """generate the cricket config data structure for this device"""
        cd = []
        self.addTargetData(cd, self.cricketDevice())
        self.addTargetData(cd, self.cricketInterfaces())
        return cd


    def addTargetData(self, cricketData, targetinfo):
        objpaq = self.primaryAq()
        if not targetinfo: return
        targetpath, targets = targetinfo
        targets = list(targets)
        targets.insert(0,objpaq.cricketTargetDefault())
        cricketData.append((targetpath, targets))


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
            self._v_targetdefault['snmp-community'] = self.snmpCommunity
            self._v_targetdefault['snmp-port'] = self.snmpPort
            if self.snmpOid.find('.1.3.6.1.4.1.9') > -1:
                self._v_targetdefault['snmp-version'] = '2c'
        return self._v_targetdefault
 
 
    def cricketDevice(self):
        """build the targets for the device itself
        use cricketTargetPath to """
        objpaq = self.primaryAq()
        targets = self.callscript(objpaq, 'scCricketDevice')
        targetpath = objpaq.cricketTargetPath()
        if not targets:
            targetdata = {}
            targetdata['target'] = objpaq.id
            crtype = objpaq.cricketDeviceType()
            if not crtype: return
            targetdata['target-type'] = crtype
            targets = (targetdata,)
        targets = self.setCricketThresholds(objpaq, targets)
        self.setCricketTargetMap(targetpath, targets) 
        return (targetpath, targets)
 

    def cricketDeviceType(self):
        """default method for getting device type
        first looks for scCricketDeviceType function that would
        calculate the type if that is not found
        it looks for zCricketDeviceType attribute
        default value is 'Device'"""
        objpaq = self.primaryAq()
        deviceType = self.callscript(objpaq, 'scCricketDeviceType')
        if not deviceType:
            deviceType = getattr(objpaq, 'zCricketDeviceType', "Device")
        try:
            lookupTargetType(objpaq, deviceType)
        except RRDObjectNotFound:
            LOG("CricketBuilder", WARNING, 
                "RRDTargetType %s for device not found" % deviceType)
        return deviceType


    def cricketInterfaces(self):
        """build the targets for device interfaces"""
        objpaq = self.primaryAq()
        targetpath = objpaq.cricketTargetPath() + '/interfaces'
        targets = []
        for interface in objpaq.interfaces.objectValuesAll():
            if not interface.adminStatus == 1: continue
            self.interfaceMultiTargets(interface, targetpath)
            inttype = objpaq.cricketInterfaceType(interface)
            if not inttype: continue
            targetdata = {}
            targetdata['target'] = interface.id
            targetdata['target-type'] = inttype
            targetdata['inst'] = interface.ifindex
            targetdata['display-name'] = interface.name
            targetdata['short-desc'] = interface.description 
            self.setCricketThreshold(interface, targetdata)
            interface.setCricketTargetMap(targetpath, targetdata)
            targets.append(targetdata)
        return (targetpath, targets)
 

    def interfaceMultiTargets(self, interface, targetpath):
        """setup graphs that have multiple targets with 
        different potentially types in one graph"""
        from Products.RRDProduct.RRDMGraph import RRDMGraph
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

        objpaq = self.primaryAq()

        type = self.callscript(objpaq, 'scCricketInterfaceType', interface)
        if type: return type
        intarray = getattr(objpaq, 'zCricketInterfaceMap', None)
        if intarray:
            intmap = {}
            for im in intarray:
                try: 
                    k, v = im.split(':') 
                    intmap[k] = v
                except: pass
        else:
            intmap = defaultmap
        cricketType = 'StandardInterface'
        if (self.getManufacturerName() == 'Cisco' 
            and interface.speed >= 100000000):
            cricketType = 'FastInterface'

        ignoreTypes = getattr(objpaq, 'zCricketInterfaceIgnoreTypes', None)
        if not ignoreTypes: ignoreTypes = defaultIgnoreTypes
        intType = interface.type
        if intType in ignoreTypes: 
            return None

        dontSendIntNames = getattr(objpaq, 'zCricketInterfaceIgnoreNames', None)
        if dontSendIntNames and re.search(dontSendIntNames,interface.name):
            return None

        if intmap.has_key(intType): 
            cricketType = intmap[intType]

        if interface.type == 'sonet' and interface.name.find('POS') == 0:
            cricketType = 'FastInterface'

        return cricketType
       

    def cricketTargetPath(self):
        """get the cricket target path
        if there is a script called scCricketTargetPath use it
        if not use the DeviceClass path of the box"""
        objpaq = self.primaryAq()
        tp = self.callscript(objpaq, 'scCricketTargetPath')
        if tp: return tp
        return objpaq.getDeviceClassPath() + '/' + self.id
    

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

