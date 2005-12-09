#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""SnmpCollector

SnmpCollector collects SNMP information and puts it into objects
mapping using snmpmaps to route the data

$Id: SnmpCollector.py,v 1.43 2004/04/01 02:58:32 edahl Exp $"""

__version__ = "$Revision: 1.43 $"[11:-2]

import os
import sys
import time
import types
import logging

import Globals
import transaction

from DateTime import DateTime
from Acquisition import aq_base


from Products.ZenRelations.utils import importClass
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.Exceptions import ZentinelException
from Products.ZenModel.Exceptions import *

from SnmpSession import SnmpSession, ZenSnmpError
from pysnmp.error import PySnmpError

class SnmpCollectorError(ZentinelException):
    """
    Problem occurred during collection.
    """
    
zenmarker = "__ZENMARKER__"

slog = logging.getLogger("SnmpCollector")

def findSnmpCommunity(context, name, community=None, port=None):
    """look for snmp community based on list we get through aq"""
    if community: communities = (community,)
    else: communities = getattr(context, "zSnmpCommunities", ())
    if not port: port = getattr(context, "zSnmpPort", 161)
    session = SnmpSession(name, timeout=3, port=port)
    oid = '.1.3.6.1.2.1.1.2.0'
    retval = None
    for community in communities: #aq
        session.community = community
        try:
            session.get(oid)
            retval = session.community
            break
        except (SystemExit, KeyboardInterrupt): raise
        except: pass #keep trying until we run out
    return retval 


class SnmpCollector(ZCmdBase):
    

    def __init__(self, noopts=0,app=None):
        ZCmdBase.__init__(self,noopts,app)
        self.cycletime = self.options.cycletime*60
        self._customMaps = []
        import CustomMaps
        CustomMaps.initCustomMaps(self)


    def collectDevices(self, deviceRoot):
        """collect snmp data and set it in objects based on roots""" 
        if type(deviceRoot) == types.StringType:
            deviceRoot = self.dmd.Devices.getOrganizer(deviceRoot)
        for device in deviceRoot.getSubDevicesGen():
            self.collectDevice(device)

                    
    def collectDevice(self, device):
        if type(device) == types.StringType:
            device = self.dmd.Devices.findDevice(self.options.device)
            if not device: 
                raise SnmpCollectorError(
                    "Device %s not found" % self.options.device)
        slog.info('Collecting device %s' % device.id)
        age = device.getSnmpLastCollection()+(self.options.collectAge/1440.0)
        if device.getSnmpStatusNumber() > 0 and age >= DateTime():
            slog.info("skipped collection of %s" % device.getId())
            return
        try:
            snmpsess = SnmpSession(device.id, 
                            community = device.zSnmpCommunity,
                            port = device.zSnmpPort)
            if self.testSnmpConnection(snmpsess):
                if device._p_jar: device._p_jar.sync() 
                if (self._checkForCiscoChange(device, snmpsess)
                    or self.options.force):
                    if self._collectCustomMaps(device, snmpsess):
                        device.setLastChange()
                    device.setSnmpLastCollection()
                    trans = transaction.get()
                    trans.note("Automated data collection by SnmpCollector.py")
                    trans.commit()
                else:
                    slog.info(
                        "skipping device %s no change detected", device.id)
            else:
                slog.warn("no valid snmp connection to %s", device.id)
        except (SystemExit, KeyboardInterrupt): raise
        except:
            slog.exception('Error collecting data from %s', device.id)
        else:
            slog.info('Collection complete')


    def testSnmpConnection(self, snmpsess):
        """test to see if snmp connection is ok"""
        try:
            data = snmpsess.get('.1.3.6.1.2.1.1.2.0')
        except (ZenSnmpError, PySnmpError):
            return False
        return True


    def _checkForCiscoChange(self, device, snmpsess):
        """Check to see if the running config changed since last poll."""
        changed = True
        if not device.snmpOid.startswith(".1.3.6.1.4.1.9"): return changed
        lastpolluptime = device.getLastPollSnmpUpTime()
        slog.debug("lastpolluptime = %s", lastpolluptime)
        try:
            lastchange = snmpsess.get('.1.3.6.1.4.1.9.9.43.1.1.1.0').values()[0]
            slog.debug("lastchange = %s", lastchange)
            if lastchange == lastpolluptime: 
                changed = False
            else:
                device.setLastPollSnmpUpTime(lastchange)
        except (ZenSnmpError, PySnmpError): pass
        return changed


    def addCustomMap(self, collector):
        """add an instance of a custom map to the collector list"""
        col = collector()
        self._customMaps.append(col)


    def _collectCustomMaps(self, device, snmpsess):
        """run through custom snmp collectors"""
        changed = False
        for custmap in self._customMaps:
            if self._passCustMap(device, custmap): continue
            if custmap.condition(device, snmpsess, slog):
                datamap = None
                try:
                    datamap = custmap.collect(device, snmpsess, slog)
                except (SystemExit, KeyboardInterrupt): raise
                except:
                    slog.exception("problem collecting snmp")
                if not datamap: continue
                try:
                    if hasattr(custmap, 'relationshipName'):
                        if self._updateRelationship(device, datamap, custmap):
                            changed = True
                    else:
                        if self._updateObject(device, datamap):
                            changed = True
                except (SystemExit, KeyboardInterrupt): raise
                except:
                    slog.exception("ERROR: implementing datamap %s",datamap)
        return changed               


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
        changed = False
        rel = getattr(device, snmpmap.relationshipName, None)
        if not rel:
            slog.warn("No relationship %s found on %s" % 
                                (snmpmap.relationshipName, device.id))
            return changed 
        relids = rel.objectIdsAll()
        for datamap in datamaps:
            if not datamap.has_key('id'):
                slog.warn("ignoring datamap no id found")
                continue
            if datamap['id'] in relids:
                if self._updateObject(rel._getOb(datamap['id']), datamap):
                    changed = True
                relids.remove(datamap['id'])
            else:
                self._createRelObject(device, snmpmap, datamap)
                changed = True
        for id in relids:
            rel._delObject(id)
            changed = True
            slog.info("Removing object %s from relation %s on obj %s",
                            id, rel.id, device.id)
        return changed


    def _updateObject(self, obj, datamap):
        """update an object using a datamap"""
        for attname, value in datamap.items():
            if attname.startswith("_"): continue
            att = getattr(aq_base(obj), attname, zenmarker)
            if att == zenmarker:
                slog.warn('attribute %s not found on object %s', 
                              attname, obj.id)
                continue
            if callable(att): 
                setter = getattr(obj, attname)
                getter = getattr(obj, attname.replace("set","get"), "")
                if getter and value != getter():
                    setter(value)
                    slog.debug(
                        "   Calling function '%s' with '%s'on object %s", 
                        attname, value, obj.id)
            elif att != value:
                setattr(aq_base(obj), attname, value) 
                slog.debug("   Set attribute %s to %s on object %s",
                               attname, value, obj.id)
        try: changed = obj._p_changed
        except: changed = False
        if getattr(aq_base(obj), "index_object", False) and changed:
            slog.debug("indexing object %s", obj.id)
            obj.index_object() 
        if not changed: obj._p_deactivate()
        return changed
        

    def _createRelObject(self, device, snmpmap, datamap):
        """create an object on a relationship using its datamap and snmpmap"""
        if snmpmap.remoteClass.find('.') > 0:
            fpath = snmpmap.remoteClass.split('.')
        else:
            raise "ObjectCreationError", \
                ("remoteClass %s must specify the module and class" 
                                            % snmpmap.remoteClass)

        constructor = importClass(snmpmap.remoteClass)
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
        transaction.savepoint()
        self._updateObject(remoteObj, datamap)
        slog.info("   Added object %s to relationship %s" 
            % (remoteObj.id, snmpmap.relationshipName))
   

    def findSnmpCommunity(self, name, device, port=161):
        """look for snmp community based on list we get through aq"""
        return findSnmpCommunity(device, name, port=port)
   

    def buildOptions(self):
        ZCmdBase.buildOptions(self)

        self.parser.add_option('--ignore',
                dest='ignoreMaps',
                default=None,
                help="Comma separated list of collection maps to ignore")
        self.parser.add_option('--collect',
                dest='collectMaps',
                default=None,
                help="Comma separated list of collection maps to use")
        self.parser.add_option('-p', '--path',
                dest='path', default="/",
                help="start path for collection ie /Servers")
        self.parser.add_option('-d', '--device',
                dest='device',
                help="Device fqdn ie www.zentinel.com")
        self.parser.add_option('--cycletime',
                dest='cycletime',default=60,type='int',
                help="run collection every x minutes")
        self.parser.add_option('--collectage',
                dest='collectAge',default=0,type='int',
                help="don't collect from devices whos collect date "
                        "is with in this many minutes")
        self.parser.add_option('--writetries',
                dest='writetries',
                default=2,
                type='int',
                help="number of times to try to write if a "
                    "readconflict is found")
        self.parser.add_option("-F", "--force",
                    dest="force", action='store_true',
                    help="force collection of config data " 
                         "(even without change to the device)")
    
    def checkoptions(self):
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

  
    def main(self):
        self.checkoptions()
        try:
            if self.options.device:
                return self.collectDevice(self.options.device)
            if not self.options.cycle:
                return self.collectDevices(self.options.path)
        except SnmpCollectorError, e:
            slog.critical(e)
            raise SystemExit
        while 1:
            startLoop = time.time()
            runTime = 0
            try:
                slog.debug("starting collector loop")
                try:
                    self.getDataRoot()
                    self.collectDevices(self.options.path)
                finally:
                    self.closedb()
                runTime = time.time()-startLoop
                slog.debug("ending collector loop")
                slog.info("loop time = %0.2f seconds",runTime)
            except SnmpCollectorError, e:
                slog.critical(e)
            except:
                slog.exception("problem in main loop")
            if runTime < self.cycletime:
                time.sleep(self.cycletime - runTime)

                    

if __name__ == '__main__':
    snmpcoll = SnmpCollector()
    snmpcoll.main()
