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

import sys
import types
import threading
import Queue
import logging
log = logging.getLogger("zen.ApplyDataMap")

import transaction

from zope.event import notify
from zope.app.container.contained import ObjectRemovedEvent, ObjectMovedEvent
from zope.app.container.contained import ObjectAddedEvent
from Acquisition import aq_base

from Products.ZenUtils.Utils import importClass, getObjByPath
from Products.Zuul.catalog.events import IndexingEvent
from Exceptions import ObjectCreationError
from Products.ZenEvents.ZenEventClasses import Change_Add,Change_Remove,Change_Set,Change_Add_Blocked,Change_Remove_Blocked,Change_Set_Blocked
from Products.ZenModel.Lockable import Lockable
import Products.ZenEvents.Event as Event

zenmarker = "__ZENMARKER__"

CLASSIFIER_CLASS = '/Classifier'

_notAscii = dict.fromkeys(range(128,256), u'?')


def isSameData(x, y):
    """
    A more comprehensive check to see if existing model data is the same as
    newly modeled data. The primary focus is comparing unsorted lists of
    dictionaries.
    """
    if isinstance(x, (tuple, list)) and isinstance(y, (tuple, list)):
        if len(x) > 0 and len(y) > 0 \
            and isinstance(x[0], dict) and isinstance(y[0], dict):

            x = set([ tuple(sorted(d.items())) for d in x ])
            y = set([ tuple(sorted(d.items())) for d in y ])
        else:
            return sorted(x) == sorted(y)

    return x == y


class ApplyDataMap(object):

    def __init__(self, datacollector=None):
        self.datacollector = datacollector


    def logChange(self, device, compname, eventClass, msg):
        if not getattr(device, 'zCollectorLogChanges', True): return
        if type(msg) == type(u''):
            msg = msg.translate(_notAscii)
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
                'agent': 'ApplyDataMap',
                'explanation': "Event sent as zCollectorLogChanges is True",
                }
            self.datacollector.dmd.ZenEventManager.sendEvent(eventDict)

        
    def processClient(self, device, collectorClient):
        """
        A modeler plugin specifies the protocol (eg SNMP, WMI) and
        the specific data to retrieve from the device (eg an OID).
        This data is then processed by the modeler plugin and then
        passed to this method to apply the results to the ZODB.

        @parameter device: DMD device object
        @type device: DMD device object
        @parameter collectorClient: results of modeling
        @type collectorClient: DMD object
        """
        log.debug("Processing data for device %s", device.id)
        devchanged = False
        try:
            for pname, results in collectorClient.getResults():
                log.debug("Processing plugin %s on device %s", pname, device.id)
                if not results: 
                    log.warn("Plugin %s did not return any results", pname)
                    continue
                plugin = self.datacollector.collectorPlugins.get(pname, None) 
                if not plugin:
                    log.warn("Unable to get plugin %s from %s", pname,
                             self.datacollector.collectorPlugins)
                    continue

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
                log.info("Changes applied")
            else:
                log.info("No change detected")
            device.setSnmpLastCollection()
            trans = transaction.get()
            trans.setUser("datacoll")
            trans.note("data applied from automated collection")
            trans.commit()
        except (SystemExit, KeyboardInterrupt): 
            raise
        except:
            transaction.abort()
            log.exception("Plugin %s device %s", pname, device.getId())


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


    def setDeviceClass(self, device, deviceClass=None):
        """
        If a device class has been passed and the current class is not /Classifier
        then move the device to the newly clssified device class.
        """
        if deviceClass and device.getDeviceClassPath().startswith(CLASSIFIER_CLASS):
            device.changeDeviceClass(deviceClass)
            

    def _applyDataMap(self, device, datamap):
        """Apply a datamap to a device.
        """
        persist = True
        try:
            device.dmd._p_jar.sync()
        except AttributeError:
            # This can occur in unit testing when the device is not persisted.
            persist = False
        
        if hasattr(datamap, "compname"):
            if datamap.compname: 
                tobj = getattr(device, datamap.compname)
            else: 
                tobj = device
            if hasattr(datamap, "relname"):
                changed = self._updateRelationship(tobj, datamap)
            elif hasattr(datamap, 'modname'):
                changed = self._updateObject(tobj, datamap)
            else:
                changed = False
                log.warn("plugin returned unknown map skipping")
        else:
            changed = False
        if changed and persist:
            device.setLastChange()
            trans = transaction.get()
            trans.setUser("datacoll")
            trans.note("data applied from automated collection")
            trans.commit()
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
                    obj = rel._getOb(objmap.id)

                    # Handle the possibility of objects changing class by
                    # recreating them. Ticket #5598.
                    existing_modname = ''
                    existing_classname = ''
                    try:
                        import inspect
                        existing_modname = inspect.getmodule(obj).__name__
                        existing_classname = obj.__class__.__name__
                    except:
                        pass

                    if objmap.modname == existing_modname and \
                        objmap.classname in ('', existing_classname):

                        objchange = self._updateObject(obj, objmap)
                        if not changed: changed = objchange
                    else:
                        rel._delObject(objmap.id)
                        objchange, obj = self._createRelObject(device, objmap, rname)
                        if not changed: changed = objchange

                    if objmap.id in relids: relids.remove(objmap.id)
                else:
                    objchange, obj = self._createRelObject(device, objmap, rname)
                    if objchange: changed = True
                    if obj and obj.id in relids: relids.remove(obj.id)
            elif isinstance(objmap, ZenModelRM):
                self.logChange(device, objmap.id, Change_Add,
                            "linking object %s to device %s relation %s" % (
                            objmap.id, device.id, rname))
                device.addRelation(rname, objmap)
                changed = True
            else:
                objchange, obj = self._createRelObject(device, objmap, rname)
                if objchange: changed = True
                if obj and obj.id in relids: relids.remove(obj.id)

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
                    # This looks confusing, and it is. The scenario is:
                    #   A collector gathers some data as a raw byte stream, 
                    #   but really it has a specific encoding specified by
                    #   by the zCollectorDecoding zProperty. Say, latin-1 or
                    #   utf-16, etc. We need to decode that byte stream to get
                    #   back a UnicodeString object. But, this version of Zope
                    #   doesn't like UnicodeString objects for a variety of
                    #   fields, such as object ids, so we then need to convert
                    #   that UnicodeString back into a regular string of bytes,
                    #   and for that we use the system default encoding, which
                    #   is now utf-8.
                    codec = obj.zCollectorDecoding or sys.getdefaultencoding()
                    value = value.decode(codec)
                    value = value.encode(sys.getdefaultencoding())
                except UnicodeDecodeError:
                    continue
            if attname[0] == '_': continue
            att = getattr(aq_base(obj), attname, zenmarker)
            if att == zenmarker:
                log.warn('The attribute %s was not found on object %s from device %s',
                              attname, obj.id, device.id)
                continue
            if callable(att): 
                setter = getattr(obj, attname)
                gettername = attname.replace("set","get") 
                getter = getattr(obj, gettername, None)
                
                if not getter:
                    
                    log.warn("getter '%s' not found on obj '%s', "
                                  "skipping", gettername, obj.id)
                    
                else:
                    
                    from plugins.DataMaps import MultiArgs
                    if isinstance(value, MultiArgs):
                        
                        args = value.args
                        change = True
                        
                    else:
                        
                        args = (value,)
                        try:
                            change = not isSameData(value, getter())
                        except UnicodeDecodeError:
                            change = True
                            
                    if change:
                        setter(*args)
                        self.logChange(device, obj, Change_Set,
                                    "calling function '%s' with '%s' on "
                                    "object %s" % (attname, value, obj.id))
                        changed = True
                        
            else:
                try:
                    change = not isSameData(att, value)
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
        if changed:
            if getattr(aq_base(obj), "index_object", False):
                log.debug("indexing object %s", obj.id)
                obj.index_object() 
            notify(IndexingEvent(obj))
        else:
            obj._p_deactivate()
        return changed
 

    def _createRelObject(self, device, objmap, relname):
        """Create an object on a relationship using its objmap.
        """
        constructor = importClass(objmap.modname, objmap.classname)
        if hasattr(objmap, 'id'):
            remoteObj = constructor(objmap.id)
        else:
            remoteObj = constructor(device, objmap)
        if remoteObj is None:
            log.debug("Constructor returned None")
            return False, None
        id = remoteObj.id
        if not remoteObj: 
            raise ObjectCreationError(
                    "failed to create object %s in relation %s" % (id, relname))

        realdevice = device.device()
        if realdevice.isLockedFromUpdates():
            objtype = ""
            try: objtype = objmap.modname.split(".")[-1] 
            except: pass
            msg = "Add Blocked: %s '%s' on %s" % (
                    objtype, id, realdevice.id)
            log.warn(msg)
            if realdevice.sendEventWhenBlocked():
                self.logEvent(realdevice, id, Change_Add_Blocked, 
                                msg, Event.Warning)
            return False, None
        rel = device._getOb(relname, None)
        if not rel:
            raise ObjectCreationError(
                    "No relation %s found on device %s" % (relname, device.id))
        changed = False
        try:
            remoteObj = rel._getOb(remoteObj.id)
        except AttributeError:
            self.logChange(realdevice, remoteObj, Change_Add,
                           "adding object %s to relationship %s" %
                           (remoteObj.id, relname))
            rel._setObject(remoteObj.id, remoteObj)
            remoteObj = rel._getOb(remoteObj.id)
            changed = True
            notify(ObjectMovedEvent(remoteObj, rel, remoteObj.id, rel, remoteObj.id))
        return self._updateObject(remoteObj, objmap) or changed, remoteObj


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
