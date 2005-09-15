#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""CommandCollector

CommandCollector collects command line information using telnet or ssh.
It works by calling a list of commandmap python scripts which return
ObjectMaps or RelationshipMaps which are then applied to a device
object by a DataCollector object.


$Id: CommandCollector.py,v 1.1 2003/09/05 01:17:53 edahl Exp $"""

__version__ = "$Revision: 1.1 $"[11:-2]

import os
import sys

from DateTime import DateTime
from Acquisition import aq_base

from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.Utils import getObjByPath


class CommandCollector(ZCmdBase):
    

    def __init__(self, noopts=0,app=None):
        ZCmdBase.__init__(self,noopts,app)


    def collect(self, deviceroot=None, devices=None):
        """collect snmp data and set it in objects based on roots""" 
        if deviceroot:
            devices = self.getDevices(deviceroot)

        for device in devices:
            self.log.info('Collecting command info from device %s' % device.id)
            if device.cmdUsername and device.cmdPassword: 
                device._p_jar.sync()
                get_transaction().note(
                    "Automated data collection by CommandCollector.py")
                get_transaction().commit()
            else:
                self.log.warn('no login information found for device %s' 
                                % device.id)
                continue

            age = device.getSnmpLastCollection()+(
                            self.options.collectAge/1440.0)
            if community and device.snmpStatus <= 0 and age <= DateTime():
                try:
                    snmpsess = SnmpSession(device.id, 
                                            community = device.snmpCommunity,
                                            port = device.snmpPort)
                    if self.testSnmpConnection(snmpsess):
                        self._collectCustomMaps(device, snmpsess)
                        device.setSnmpLastCollection()
                        get_transaction().commit()
                    else:
                        self.log.warn(
                            "no valid snmp connection to %s" % device.getId())
                except:
                    self.log.exception('Error collecting data from %s' 
                                        % device.id)
            else:
                self.log.info("skipped collection of %s" % device.getId())



    def collectCustomMaps(self, device, snmpsess):
        """run through custom snmp collectors"""
        for custmap in self._customMaps:
            if self._passCustMap(device, custmap):
                continue
            if custmap.condition(device, snmpsess, self.log):
                datamap = None
                try:
                    datamap = custmap.collect(device, snmpsess, self.log)
                except:
                    self.log.exception("problem collecting snmp")
                if datamap:
                    try:
                        device._p_jar.sync()
                        if hasattr(custmap, 'relationshipName'):
                            self._updateRelationship(device, datamap, custmap)
                        else:
                            self._updateObject(device, datamap)
                        get_transaction().note(
                            "Automated data collection by CommandCollector.py")
                        get_transaction().commit()
                    except:
                        self.log.exception("ERROR: implementing datamap %s"
                                                % datamap)
   

    def getDevices(self, deviceroot):
        "get all the devices by meta_type this needs to change to inheritance"
        return deviceroot.getSubDevices()

        
    def buildOptions(self):
        ZCmdBase.buildOptions(self)

        self.parser.add_option('-i', '--ignore',
                dest='ignoreMaps',
                default=None,
                help="Comma separated list of collection maps to ignore")
        self.parser.add_option('-c', '--collect',
                dest='collectMaps',
                default=None,
                help="Comma separated list of collection maps to use")
        self.parser.add_option('-p', '--path',
                dest='path',
                help="start path for collection ie /Devices")
        self.parser.add_option('-d', '--device',
                dest='device',
                help="Device path ie /Devices/Servers/www.confmon.com")
        self.parser.add_option('-a', '--collectAge',
                dest='collectAge',
                default=0,
                type='int',
                help="don't collect from devices who's collect date " +
                        "is with in this many minutes")

    
    def mainCollector(self):
        #FIXME this should use args but it isn't getting setup correctly!!! -EAD
        if (not self.options.path and 
            not self.options.device):
           print "no device or path specified must have one!"
        devices = None
        droot = None
        if self.options.device:
            device = self.getDmdObj(self.options.device)
            devices = (device,)
        if self.options.path:
            droot = self.getDmdObj(self.options.path)
        if self.options.ignoreMaps and self.options.collectMaps:
            print "--ignore and --collect are mutually exclusive"
            sys.exit(1)
        if self.options.ignoreMaps:
            self.options.ignoreMaps = self.options.ignoreMaps.split(',')
        if self.options.collectMaps:
            self.options.collectMaps = self.options.collectMaps.split(',')
        if droot or devices:
            self.collect(deviceroot=droot, devices=devices)
        else:
            print "unable to locate device or path specified"
            sys.exit(1)


#InitializeClass(CommandCollector)

if __name__ == '__main__':
    snmpcoll = CommandCollector()
    snmpcoll.mainCollector()
