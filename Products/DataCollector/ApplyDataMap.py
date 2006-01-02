#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

import time
import threading
import Queue

import transaction

from Acquisition import aq_base

from Products.ZenUtils.Utils import importClass

from Exceptions import *

import logging
log = logging.getLogger("ApplyDataMap")

zenmarker = "__ZENMARKER__"

class ApplyDataMap(object):

    def __init__(self, datacollector):
        self.datacollector = datacollector


    def processClient(self, device, collectorClient):
        """Apply datamps to device.
        """
        try:
            device._p_jar.sync()
            devchanged = False
            for pname, results in collectorClient.getResults():
                if not self.datacollector.collectorPlugins.has_key(pname): 
                    continue
                plugin = self.datacollector.collectorPlugins[pname]
                results = plugin.preprocess(results, log)
                datamap = plugin.process(device, results, log)
                changed = self._applyDataMap(device, datamap)
                if changed: devchanged=True
            if devchanged:
                device.setLastChange()
                trans = transaction.get()
                trans.setUser("datacoll")
                trans.note("data applied from automated collection")
                trans.commit()
            else:
                log.debug("no change skipping commit")
        except (SystemExit, KeyboardInterrupt): raise
        except:
            transaction.abort()
            log.exception("applying datamaps to device %s",device.getId())


    def _applyDataMap(self, device, datamap):
        """Apply a datamap to a device.
        """
        tobj = device
        if datamap.compname: 
            tobj = getattr(device, datamap.compname)
        if getattr(datamap, "relname"):
            changed = self._updateRelationship(tobj, datamap)
        else:
            changed = self._updateObject(tobj, datamap)
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
        for objmap in relmap:
            from Products.ZenModel.ZenModelRM import ZenModelRM
            if hasattr(objmap, 'modname') and hasattr(objmap, 'id'):
                if objmap.id in relids:
                    obj = rel._getOb(objmap.id) 
                    changed = self._updateObject(obj, objmap)
                    relids.remove(objmap.id)
                else:
                    self._createRelObject(device, objmap, rname)
                    changed = True
            elif isinstance(objmap, ZenModelRM):
                log.debug("linking object %s to device %s relation %s",
                                    objmap.id, device.id, rname)
                device.addRelation(rname, objmap)
                changed = True
            else:
                log.warn("ignoring objmap no id found")
        for id in relids: 
            log.info("removing object %s from rel %s on device %s",
                        id, rname, device.id)
            rel._delObject(id)
        if relids: changed=True
        return changed


    def _updateObject(self, obj, objmap):
        """Update an object using a objmap.
        """
        change = False
        for attname, value in objmap.items():
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
                elif value != getter():
                    setter(value)
                    log.debug("calling function '%s' with '%s' on "
                               "object %s", attname, value, obj.id)
                    changed = True            
            elif att != value:
                setattr(aq_base(obj), attname, value) 
                log.debug("set attribute '%s' to '%s' on object '%s'",
                           attname, value, obj.id)
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
        self._updateObject(remoteObj, objmap)
        log.debug("added object %s to relationship %s", remoteObj.id, relname)

    


class ApplyDataMapThread(threading.Thread, ApplyDataMap):
    """
    Thread that applies datamaps to a device.  It reads from a queue that 
    should have tuples of (devid, datamaps) where devid is the primaryId to
    the device and datamps is a list of datamaps to apply.  Cache is synced at
    the start of each transaction and there is one transaction per device.
    """

    def __init__(self, app):
        threading.Thread.__init__(self)
        ApplyDataMap.__init__(self)
        self.setName("ApplyDataMapThread")
        self.setDaemon(1)
        self.app = app
        log.debug("Thread conn:%s", self.app._p_jar)
        self.inputqueue = Queue.Queue()
        self.done = False


    def applyDataMaps(self, device, datamaps):
        """Add a device and its datamaps to the threads inputqueue.
        """
        devpath = device.getPrimaryPath()
        self.inputqueue.put((devpath, datamaps))


    def run(self):
        """Process datamaps as they are passed in from a data collector.
        """
        while not self.done or not self.inputqueue.empty():
            try:
                devpath, datamaps = self.inputqueue.get(True,1)
                log.debug("applying datamaps to %s", "/".join(devpath))
                device = self.app.unrestrictedTraverse(devpath)
                ApplyDataMap.applyDataMaps(self, device, datamaps)
            except Queue.Empty: pass 
            except (SystemExit, KeyboardInterrupt): raise
            except:
                transaction.abort()
                log.exception("applying datamaps to device %s",
                                    device.getId())
