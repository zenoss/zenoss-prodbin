#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""SnmpCollector

SnmpCollector collects SNMP information and puts it into objects
mapping using snmpmaps to route the data

$Id: SnmpCollector.py,v 1.43 2004/04/01 02:58:32 edahl Exp $"""

__version__ = "$Revision: 1.43 $"[11:-2]

import os
import sys

import Globals
import ZODB

from DateTime import DateTime
from Acquisition import aq_base

from Products.Confmon.Exceptions import *

from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.Utils import getObjByPath

from SnmpSession import SnmpSession
from pysnmp.error import PySnmpError

class SnmpCollector(ZCmdBase):
    

    def __init__(self, noopts=0,app=None):
        ZCmdBase.__init__(self,noopts,app)
        self._customMaps = []
        import CustomMaps
        CustomMaps.initCustomMaps(self)
        


    def collectDevices(self, deviceRoot):
        """collect snmp data and set it in objects based on roots""" 
        for device in deviceRoot.getSubDevices():
            writetries = self.options.writetries
            while writetries:
                try:
                    self.collectDevice(device)
                    break
                except ZODB.POSException.ReadConflictError:
                    device._p_jar.sync()
                    writetries -= 1
                except SystemExit: raise
                except:  
                    self.log.exception(
                        "Failure collecting device %s" % device.getId())
                    break

                    
    def collectDevice(self, device):
        self.log.info('Collecting device %s' % device.id)
        community = device.snmpCommunity
        if not community:
            community = self.findSnmpCommunity(device.id, device,
                                                port=device.snmpPort)
            if community: 
                device.snmpCommunity = community
                device.resetSnmpStatus()
                self.log.info("Found community %s for device %s" % 
                                (community, device.id))
                get_transaction().note(
                    "Automated data collection by SnmpCollector.py")
                get_transaction().commit()
            else:
                self.log.warn('no communty not found for device %s' 
                                % device.id)
                return 

        age = device.getSnmpLastCollection()+(
                        self.options.collectAge/1440.0)
        if (community and device.getSnmpStatusNumber() <= 0 
            and age <= DateTime()):
            try:
                snmpsess = SnmpSession(device.id, 
                                community = device.snmpCommunity,
                                port = device.snmpPort)
                if self.testSnmpConnection(snmpsess):
                    self._collectCustomMaps(device, snmpsess)
                    device.setSnmpLastCollection()
                    get_transaction().note(
                        "Automated data collection by SnmpCollector.py")
                    get_transaction().commit()
                else:
                    self.log.warn(
                        "no valid snmp connection to %s" 
                            % device.getId())
            except:
                self.log.exception('Error collecting data from %s' 
                                    % device.id)
        else:
            self.log.info("skipped collection of %s" % device.getId())


    def testSnmpConnection(self, snmpsess):
        """test to see if snmp connection is ok"""
        try:
            data = snmpsess.get('.1.3.6.1.2.1.1.2.0')
        except SystemExit: raise
        except PySnmpError, msg:
            self.log.debug(msg)
            return None
        return 1


    def addCustomMap(self, collector):
        """add an instance of a custom map to the collector list"""
        col = collector()
        self._customMaps.append(col)


    def _collectCustomMaps(self, device, snmpsess):
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
                        #device._p_jar.sync()
                        if hasattr(custmap, 'relationshipName'):
                            self._updateRelationship(device, datamap, custmap)
                        else:
                            self._updateObject(device, datamap)
                        get_transaction().note(
                            "Automated data collection by SnmpCollector.py")
                        get_transaction().commit()
                    except:
                        self.log.exception("ERROR: implementing datamap %s"
                                                % datamap)
   

    def _passCustMap(self, device, custmap):
        """check to see if we should use this map"""
        device = device.primaryAq()
        aqIgnoreMaps = getattr(device, 'zSnmpCollectorIgnoreMaps', [])
        aqCollectMaps = getattr(device, 'zSnmpCollectorCollectMaps', [])
        if len(aqCollectMaps) == 1 and not aqCollectMaps[0]:
            aqCollectMaps = []
        mapname = custmap.__class__.__name__
        if (
            (self.options.ignoreMaps and mapname in self.options.ignoreMaps)
            or
            (self.options.collectMaps 
                and not mapname in self.options.collectMaps)
            or
            (aqIgnoreMaps and mapname in aqIgnoreMaps)
            or
            (aqCollectMaps and not mapname in aqCollectMaps)
            ):
            return 1


    def _updateRelationship(self, device, datamaps, snmpmap):
        """populate the relationship with collected data"""
        rel = getattr(device, snmpmap.relationshipName, None)
        if rel:
            relids = rel.objectIdsAll()
            for datamap in datamaps:
                if datamap.has_key('id'):
                    if datamap['id'] in relids:
                        self._updateObject(rel._getOb(datamap['id']), datamap)
                        relids.remove(datamap['id'])
                    else:
                        self._createRelObject(device, snmpmap, datamap)
                else:
                    self.log.warn("ignoring datamap no id found")
            for id in relids:
                rel._delObject(id)
        else:
            self.log.warn("No relationship %s found on %s" % 
                                (snmpmap.relationshipName, device.id))




    def _updateObject(self, obj, datamap):
        """update an object using a datamap"""
        for attname, value in datamap.items():
            if attname[0] == '_': continue
            if hasattr(aq_base(obj), attname):
                try:
                    att = getattr(obj, attname)
                    if callable(att):
                        att(value)
                    else:
                        if att != value:
                                setattr(aq_base(obj), attname, value) 
                except:
                    self.log.exception("ERROR: setting attribute %s"
                                            % attname)
                self.log.debug("   Set attribute %s to %s on object %s" 
                                % (attname, value, obj.id))
            else:
                self.log.warn('attribute %s not found on object %s' 
                                % (attname, obj.id))
        obj.index_object() #FIXME do we really need this?
        

    def _createRelObject(self, device, snmpmap, datamap):
        """create an object on a relationship using its datamap and snmpmap"""
        if snmpmap.remoteClass.find('.') > 0:
            fpath = snmpmap.remoteClass.split('.')
        else:
            raise "ObjectCreationError", \
                ("remoteClass %s must specify the module and class" 
                                            % snmpmap.remoteClass)

        constructor = (self._lookupClass(snmpmap.remoteClass)
                    or getObjByPath(self.app.Control_Panel.Products, fpath))
        if constructor:
            remoteObj = constructor(datamap['id'])
            if not remoteObj: 
                raise "ObjectCreationError", ("failed to create object for %s" 
                                % datamap['id'])
            rel = device._getOb(snmpmap.relationshipName, None) 
            if rel:
                rel._setObject(remoteObj.id, remoteObj)
            else:
                raise "ObjectCreationError", \
                    ("No relation %s found on device %s" 
                     % (snmpmap.relationshipName, device.id))
            remoteObj = rel._getOb(remoteObj.id)
            self._updateObject(remoteObj, datamap)
            self.log.debug("   Added object %s to relationship %s" 
                % (remoteObj.id, snmpmap.relationshipName))
        else:
            raise "ObjectCreationError", \
                ("Can not find factory function for %s" 
                    % snmpmap.remoteClass)
   

    def _lookupClass(self, productName):
        """look in sys.modules for our class"""
        from Products.ZenUtils.Utils import lookupClass
        return lookupClass(productName)


    def findSnmpCommunity(self, name, device, port=161):
        """look for snmp community based on list we get through aq"""
        session = SnmpSession(name, timeout=3, port=port)
        oid = '.1.3.6.1.2.1.1.2.0'
        retval = None
        for community in device.snmp_communities: #aq
            session.community = community
            try:
                session.get(oid)
                retval = session.community
                break
            except: pass #keep trying until we run out
        return retval 
   

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
                help="don't collect from devices whos collect date "
                        "is with in this many minutes")
        self.parser.add_option('--writetries',
                dest='writetries',
                default=2,
                type='int',
                help="number of times to try to write if a "
                    "readconflict is found")

   
    def mainCollector(self):
        #FIXME this should use args but it isn't getting setup correctly!!! -EAD
        if (not self.options.path and 
            not self.options.device):
           print "no device or path specified must have one!"
        
        if self.options.ignoreMaps and self.options.collectMaps:
            print "--ignore and --collect are mutually exclusive"
            sys.exit(1)
        if self.options.ignoreMaps:
            self.options.ignoreMaps = self.options.ignoreMaps.split(',')
        if self.options.collectMaps:
            self.options.collectMaps = self.options.collectMaps.split(',')

        if self.options.device:
            device = self.getDmdObj(self.options.device)
            if not device:
                raise PathNotFoundError, \
                    "unable to locate device %s" % self.options.device
            self.collectDevice(device)
        if self.options.path:
            droot = self.getDmdObj(self.options.path)
            if not droot:
                raise PathNotFoundError, \
                    "unable to find path %s" % self.options.path
            self.collectDevices(droot)
        else:
            print "unable to locate device or path specified"
            sys.exit(1)


#InitializeClass(SnmpCollector)

if __name__ == '__main__':
    snmpcoll = SnmpCollector()
    snmpcoll.mainCollector()
