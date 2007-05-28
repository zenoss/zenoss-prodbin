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

import time
import types
import threading
import Queue

import transaction

from Acquisition import aq_base

from Products.ZenUtils.Utils import importClass, getObjByPath
from Exceptions import *
from Products.ZenEvents.ZenEventClasses import Change_Add,Change_Remove,Change_Set,Change_Add_Blocked,Change_Remove_Blocked,Change_Set_Blocked
from Products.ZenModel.Lockable import Lockable
import Products.ZenEvents.Event as Event
import logging
log = logging.getLogger("zen.ApplyDataMap")

zenmarker = "__ZENMARKER__"

class ApplyDataMap(object):

    def __init__(self, datacollector=None):
        self.datacollector = datacollector


    def logChange(self, device, compname, eventClass, msg):
        if not getattr(device, 'zCollectorLogChanges', True): return
        self.logEvent(device, compname, eventClass, msg, Event.Info)


    def logEvent(self, device, component, eventClass, msg, severity):
        ''' Used to report a change to a device model.  Logs the given msg
        to log.info and creates an event.
        '''
        device = device.device()
        compname = ""
        try:
            compname = getattr(component, 'id', component)
            if hasattr(component, 'name') and callable(component.name):
                    compname = component.name()
            elif device.id == compname:
                compname = ""
        except: pass
        log.debug(msg)
        devname = device.device().id
        if (self.datacollector
            # why is this line here?  Blocks evnets from model in zope
            #and getattr(self.datacollector, 'generateEvents', False) 
            and getattr(self.datacollector, 'dmd', None)):
            eventDict = {
                'eventClass': eventClass,
                'device': devname,
                'component': compname,
                'summary': msg,
                'severity': severity,
                }
            self.datacollector.dmd.ZenEventManager.sendEvent(eventDict)

        
    def processClient(self, device, collectorClient):
        """Apply datamps to device.
        """
        log.debug("processing data for device %s", device.id)
        devchanged = False
        try:
            #clientresults = collectorClient.getResults()
            #clientresults.sort()
            #for pname, results in clientresults:
            for pname, results in collectorClient.getResults():
                log.debug("processing plugin %s on device %s", pname, device.id)
                if not results: 
                    log.warn("plugin %s no results returned", pname)
                    continue
                plugin = self.datacollector.collectorPlugins.get(pname, None) 
                if not plugin: continue
                results = plugin.preprocess(results, log)
                datamaps = plugin.process(device, results, log)
                #allow multiple maps to be returned from one plugin
                if (type(datamaps) != types.ListType 
                    and type(datamaps) != types.TupleType):
                    datamaps = [datamaps,]
                for datamap in datamaps:
                    changed = self._applyDataMap(device, datamap)
                    if changed: devchanged=True
            if devchanged:
                device.setLastChange()
                log.info("changes applied")
            else:
                log.info("no change detected")
            device.setSnmpLastCollection()
            trans = transaction.get()
            trans.setUser("datacoll")
            trans.note("data applied from automated collection")
            trans.commit()
        except (SystemExit, KeyboardInterrupt): 
            raise
        except:
            transaction.abort()
            log.exception("plugin %s device %s", pname, device.getId())


    def applyDataMap(self, device, datamap, relname="", compname="",modname=""):
        """Apply a datamap passed as a list of dicts through XML-RPC.
        """
        from plugins.DataMaps import RelationshipMap, ObjectMap
        if relname:
            datamap = RelationshipMap(relname=relname, compname=compname, 
                                modname=modname, objmaps=datamap)
        else:
            datamap = ObjectMap(datamap, compname=compname, modname=modname)
        self._applyDataMap(device, datamap)



    def _applyDataMap(self, device, datamap):
        """Apply a datamap to a device.
        """
        changed = False
        tobj = device
        if getattr(datamap, "compname", None) is None: return changed
        if datamap.compname: 
            tobj = getattr(device, datamap.compname)
        if hasattr(datamap, "relname"):
            changed = self._updateRelationship(tobj, datamap)
        elif hasattr(datamap, 'modname'):
            changed = self._updateObject(tobj, datamap)
        else:
            log.warn("plugin returned unknown map skipping")
        return changed
            
        
    def _updateRelationship(self, device, relmap):
        """Add/Update/Remote objects to the target relationship.
        """
        changed = False
        rname = relmap.relname
        rel = getattr(device, rname, None)
        if not rel:
            log.warn("no relationship:%s found on:%s", 
                          relmap.relname, device.id)
            return changed
        relids = rel.objectIdsAll()
        seenids = {}
        for objmap in relmap:
            from Products.ZenModel.ZenModelRM import ZenModelRM
            if hasattr(objmap, 'modname') and hasattr(objmap, 'id'):
                if seenids.has_key(objmap.id):
                    seenids[objmap.id] += 1
                    objmap.id = "%s_%s" % (objmap.id, seenids[objmap.id])
                else: 
                    seenids[objmap.id] = 1
                if objmap.id in relids:
                    objchange = False
                    obj = rel._getOb(objmap.id)
                    objchange = self._updateObject(obj, objmap)
                    if not changed: changed = objchange
                    relids.remove(objmap.id)
                else:
                    changed = self._createRelObject(device, objmap, rname)
            elif isinstance(objmap, ZenModelRM):
                self.logChange(device, objmap.id, Change_Add,
                            "linking object %s to device %s relation %s" % (
                            objmap.id, device.id, rname))
                device.addRelation(rname, objmap)
                changed = True
            else:
                log.warn("ignoring objmap no id found")
        for id in relids: 
            obj = rel._getOb(id)
            if isinstance(obj, Lockable) and obj.isLockedFromDeletion():
                objname = obj.id
                try: objname = obj.name()
                except: pass
                msg = "Deletion Blocked: %s '%s' on %s" % (
                        obj.meta_type, objname,obj.device().id)
                log.warn(msg)
                if obj.sendEventWhenBlocked():
                    self.logEvent(device, obj, Change_Remove_Blocked, 
                                    msg, Event.Warning)
                continue
            self.logChange(device, obj, Change_Remove,
                    "removing object %s from rel %s on device %s" % (
                    id, rname, device.id))
            rel._delObject(id)
        if relids: changed=True
        return changed


    def _updateObject(self, obj, objmap):
        """Update an object using a objmap.
        """
        changed = False
        device = obj.device()
        if isinstance(obj, Lockable) and obj.isLockedFromUpdates():
            if device.id == obj.id:
                msg = 'Update Blocked: %s' % device.id
            else:
                objname = obj.id
                try: objname = obj.name()
                except: pass
                msg = "Update Blocked: %s '%s' on %s" % (
                        obj.meta_type, objname ,device.id)
            log.warn(msg)
            if obj.sendEventWhenBlocked():
                self.logEvent(device, obj,Change_Set_Blocked,msg,Event.Warning)
            return changed
        for attname, value in objmap.items():
            if type(value) == type(''):
                try:
                    value.encode('ascii')
                except UnicodeDecodeError:
                    decoding = obj.zCollectorDecoding
                    value = value.decode(decoding)
            if attname[0] == '_': continue
            att = getattr(aq_base(obj), attname, zenmarker)
            if att == zenmarker:
                log.warn('attribute %s not found on object %s',
                              attname, obj.id)
                continue
            if callable(att): 
                setter = getattr(obj, attname)
                gettername = attname.replace("set","get") 
                getter = getattr(obj, gettername, None)
                if not getter:
                    log.warn("getter '%s' not found on obj '%s', "
                                  "skipping", gettername, obj.id)
                else:
                    try:
                        change = value != getter()
                    except UnicodeDecodeError:
                        change = True
                    if change:
                        setter(value)
                        self.logChange(device, obj, Change_Set,
                                    "calling function '%s' with '%s' on "
                                    "object %s" % (attname, value, obj.id))
                        changed = True            
            else:
                try:
                    change = att != value
                except UnicodeDecodeError:
                    change = True
                if change:
                    setattr(aq_base(obj), attname, value) 
                    self.logChange(device, obj, Change_Set,
                                   "set attribute '%s' "
                                   "to '%s' on object '%s'" %
                                   (attname, value, obj.id))
                    changed = True
        if not changed:
            try: changed = obj._p_changed
            except: pass
        if getattr(aq_base(obj), "index_object", False) and changed:
            log.debug("indexing object %s", obj.id)
            obj.index_object() 
        if not changed: obj._p_deactivate()
        return changed
 

    def _createRelObject(self, device, objmap, relname):
        """Create an object on a relationship using its objmap.
        """
        realdevice = device.device()
        if realdevice.isLockedFromUpdates():
            objtype = ""
            try: objtype = objmap.modname.split(".")[-1] 
            except: pass
            msg = "Add Blocked: %s '%s' on %s" % (
                    objtype, objmap.id, realdevice.id)
            log.warn(msg)
            if realdevice.sendEventWhenBlocked():
                self.logEvent(realdevice, objmap.id, Change_Add_Blocked, 
                                msg, Event.Warning)
            return False
        id = objmap.id
        constructor = importClass(objmap.modname, objmap.classname)
        remoteObj = constructor(id)
        if not remoteObj: 
            raise ObjectCreationError(
                    "failed to create object %s in relation %s" % (id, relname))
        rel = device._getOb(relname, None) 
        if rel:
            rel._setObject(remoteObj.id, remoteObj)
        else:
            raise ObjectCreationError(
                    "No relation %s found on device %s" % (relname, device.id))
        remoteObj = rel._getOb(remoteObj.id)
        self.logChange(realdevice, remoteObj, Change_Add,
                        "adding object %s to relationship %s" % (
                        remoteObj.id, relname))
        self._updateObject(remoteObj, objmap)
        return True


    def stop(self): pass 


class ApplyDataMapThread(threading.Thread, ApplyDataMap):
    """
    Thread that applies datamaps to a device.  It reads from a queue that 
    should have tuples of (devid, datamaps) where devid is the primaryId to
    the device and datamps is a list of datamaps to apply.  Cache is synced at
    the start of each transaction and there is one transaction per device.
    """

    def __init__(self, datacollector, app):
        threading.Thread.__init__(self)
        ApplyDataMap.__init__(self, datacollector)
        self.setName("ApplyDataMapThread")
        self.setDaemon(1)
        self.app = app
        log.debug("Thread conn:%s", self.app._p_jar)
        self.inputqueue = Queue.Queue()
        self.done = False


    def processClient(self, device, collectorClient):
        """Apply datamps to device.
        """
        devpath = device.getPrimaryPath()
        self.inputqueue.put((devpath, collectorClient))


    def run(self):
        """Process collectorClients as they are passed in from a data collector.
        """
        log.info("starting applyDataMap thread")
        while not self.done or not self.inputqueue.empty():
            devpath = ()
            try:
                devpath, collectorClient = self.inputqueue.get(True,1)
                self.app._p_jar.sync()
                device = getObjByPath(self.app, devpath)
                ApplyDataMap.processClient(self, device, collectorClient)
            except Queue.Empty: pass 
            except (SystemExit, KeyboardInterrupt): raise
            except:
                transaction.abort()
                log.exception("processing device %s", "/".join(devpath))
        log.info("stopping applyDataMap thread")


    def stop(self):
        """Stop the thread once all devices are processed.
        """
        self.done = True
        self.join()
