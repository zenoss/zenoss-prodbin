##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import sys
from collections import defaultdict
import logging
log = logging.getLogger("zen.ApplyDataMap")

import transaction

from ZODB.transact import transact
from zope.event import notify
from zope.container.contained import ObjectMovedEvent
from Acquisition import aq_base

from Products.ZenUtils.Utils import importClass
from Products.Zuul.catalog.events import IndexingEvent
from Products.ZenUtils.events import pausedAndOptimizedIndexing
from Products.DataCollector.Exceptions import ObjectCreationError
from Products.ZenEvents.ZenEventClasses import Change_Add,Change_Remove,Change_Set,Change_Add_Blocked,Change_Remove_Blocked,Change_Set_Blocked
from Products.ZenModel.Lockable import Lockable
from Products.ZenEvents import Event
from Products.ZenRelations.ToManyContRelationship import ToManyContRelationship
from zExceptions import NotFound

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
        if x and y and isinstance(x[0], dict) and isinstance(y[0], dict):
            x = set(tuple(sorted(d.items())) for d in x)
            y = set(tuple(sorted(d.items())) for d in y)
        else:
            return sorted(x) == sorted(y)

    return x == y


class ApplyDataMap(object):

    def __init__(self, datacollector=None):
        self.datacollector = datacollector
        self._dmd = None
        if datacollector:
            self._dmd = getattr(datacollector, 'dmd', None)


    def logChange(self, device, compname, eventClass, msg):
        if not getattr(device, 'zCollectorLogChanges', True): return
        if isinstance(msg, unicode):
            msg = msg.translate(_notAscii)
        self.logEvent(device, compname, eventClass, msg, Event.Info)


    def logEvent(self, device, component, eventClass, msg, severity):
        ''' Used to report a change to a device model.  Logs the given msg
        to log.info and creates an event.
        '''
        log.debug(msg)
        if self._dmd:
            device = device.device()
            # Support string and ZenModelRM component arguments
            compname = getattr(component, 'id', component)
            if device.id == compname:
                compname = ""
            eventDict = {
                'eventClass': eventClass,
                'device': device.id,
                'component': compname,
                'summary': msg,
                'severity': severity,
                'agent': 'ApplyDataMap',
                'explanation': "Event sent as zCollectorLogChanges is True",
            }
            self._dmd.ZenEventManager.sendEvent(eventDict)


    def applyDataMap(self, device, datamap, relname="", compname="", modname="", parentId=""):
        """Apply a datamap passed as a list of dicts through XML-RPC.
        """
        from Products.DataCollector.plugins.DataMaps import RelationshipMap, ObjectMap
        if relname:
            datamap = RelationshipMap(relname=relname, compname=compname,
                                      modname=modname, objmaps=datamap, parentId=parentId)
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


    @transact
    def _applyDataMap(self, device, datamap):
        """Apply a datamap to a device.
        """
        # This can cause breakage in unit testing when the device is persisted.
        if not hasattr(device.dmd, 'zport'):
            transaction.abort()

        # There's the potential for a device to change device class during
        # modeling. Due to this method being run within a retrying @transact,
        # this will result in device losing its deviceClass relationship.
        if not device.deviceClass():
            new_device = device.dmd.Devices.findDeviceByIdExact(device.id)
            if new_device:
                log.debug("%s changed device class to %s during modeling",
                    new_device.titleOrId(), new_device.getDeviceClassName())

                device = new_device
            else:
                log.error("%s lost its device class during modeling",
                    device.titleOrId())

                return False

        changed = False

        from Products.DataCollector.plugins.DataMaps import RelationshipMap, ObjectMap, dicts_to_datamaps
        if not isinstance(datamap, (RelationshipMap, ObjectMap)):
             datamap = dicts_to_datamaps(datamap)[0]

        if hasattr(datamap, "parentId") or hasattr(datamap, "compname"):
            if getattr(datamap, "parentId", None):
                if device.id == datamap.parentId:
                    tobj = device
                else:
                    tobj = device.componentSearch(id=datamap.parentId)
                    if len(tobj) == 1:
                        tobj = tobj[0].getObject()
                    elif len(tobj) < 1:
                        log.warn(
                            "Unable to find a matching parentId '%s'",
                            datamap.parentId)
                        return False
                    else:
                        log.warn(
                            "Too many object matching parentId '%s'.  Make sure all components have a unique id.",
                            datamap.parentId)
                        return False
            elif datamap.compname:
                try:
                    tobj = device.getObjByPath(datamap.compname)
                except NotFound:
                    log.warn("Unable to find compname '%s'", datamap.compname)
                    return False
            else:
                tobj = device

            # Delay indexing until the map has been fully processed
            # so we index the minimum amount
            with pausedAndOptimizedIndexing():
                if hasattr(datamap, "relname"):
                    changed = self._updateRelationship(tobj, datamap)
                elif hasattr(datamap, 'modname'):
                    changed = self._updateObject(tobj, datamap)
                else:
                    log.warn("plugin returned unknown map skipping")

        if not changed:
            transaction.abort()
        else:
            device.setLastChange()
            trans = transaction.get()
            trans.setUser("datacoll")
            trans.note("data applied from automated collection")
        return changed


    def _updateRelationship(self, device, relmap):
        """Add/Update/Remote objects to the target relationship.
        """
        changed = False
        rname = relmap.relname
        rel = getattr(device, rname, None)
        if not rel:
            log.warn("no relationship:%s found on:%s (%s %s)",
                          relmap.relname, device.id, device.__class__, device.zPythonClass)
            return changed
        relids = set(rel.objectIdsAll())
        seenids = defaultdict(int)
        for objmap in relmap:
            from Products.ZenModel.ZenModelRM import ZenModelRM
            if hasattr(objmap, 'modname') and hasattr(objmap, 'id'):
                objmap_id = objmap.id
                seenids[objmap_id] += 1
                if seenids[objmap_id] > 1:
                    objmap_id = objmap.id = "%s_%s" % (objmap_id, seenids[objmap_id])
                if objmap_id in relids:
                    obj = rel._getOb(objmap_id)

                    # Handle the possibility of objects changing class by
                    # recreating them. Ticket #5598.
                    existing_modname = ''
                    existing_classname = ''
                    try:
                        import inspect
                        existing_modname = inspect.getmodule(obj).__name__
                        existing_classname = obj.__class__.__name__
                    except Exception:
                        pass

                    if objmap.modname == existing_modname and \
                        objmap.classname in ('', existing_classname):

                        changed |= self._updateObject(obj, objmap)
                    else:
                        rel._delObject(objmap_id)
                        objchange, obj = self._createRelObject(device, objmap, rname)
                        if obj:
                            relids.discard(obj.id)
                        changed |= objchange

                    relids.discard(objmap_id)
                else:
                    objchange, obj = self._createRelObject(device, objmap, rname)
                    changed |= objchange
                    if obj:
                        relids.discard(obj.id)
            elif isinstance(objmap, ZenModelRM):
                self.logChange(device, objmap.id, Change_Add,
                            "linking object %s to device %s relation %s" % (
                            objmap.id, device.id, rname))
                device.addRelation(rname, objmap)
                changed = True
            else:
                objchange, obj = self._createRelObject(device, objmap, rname)
                changed |= objchange
                if obj:
                    relids.discard(obj.id)

        for id in relids:
            obj = rel._getOb(id)
            if isinstance(obj, Lockable) and obj.isLockedFromDeletion():
                objname = obj.id
                try: objname = obj.name()
                except Exception: pass
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
            changed = True
        
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
                except Exception: pass
                msg = "Update Blocked: %s '%s' on %s" % (
                        obj.meta_type, objname ,device.id)
            log.warn(msg)
            if obj.sendEventWhenBlocked():
                self.logEvent(device, obj,Change_Set_Blocked,msg,Event.Warning)
            return changed
        for attname, value in objmap.items():
            if attname.startswith('_'):
                continue
            if isinstance(value, basestring):
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
                    # We don't know what to do with this, so don't set the
                    # value
                    continue
            att = getattr(aq_base(obj), attname, zenmarker)
            if att is zenmarker:
                log.warn('The attribute %s was not found on object %s from device %s',
                              attname, obj.id, device.id)
                continue
            if callable(att):
                getter = None
                if attname.startswith("set"):
                    getter = getattr(obj, "get" + attname[3:], None)
                if not getter or not callable(getter):
                    log.warn("getter for '%s' not found on obj '%s', skipping",
                             attname, obj.id)
                    continue
                from Products.DataCollector.plugins.DataMaps import MultiArgs
                if isinstance(value, MultiArgs):
                    args = value.args
                    value_to_test = value.args
                else:
                    args = (value,)
                    value_to_test = value
                try:
                    change = not isSameData(value_to_test, getter())
                except UnicodeDecodeError:
                    change = True
                if change:
                    setter = getattr(obj, attname)
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
            changed = getattr(obj, '_p_changed', False)
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
            except Exception: pass
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
                    "No relation %s found on object %s (%s)" % (relname, device.id, device.__class__ ))
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
            if not isinstance(rel, ToManyContRelationship):
                notify(ObjectMovedEvent(remoteObj, rel, remoteObj.id, rel, remoteObj.id))
        return self._updateObject(remoteObj, objmap) or changed, remoteObj


    def stop(self):
        pass

