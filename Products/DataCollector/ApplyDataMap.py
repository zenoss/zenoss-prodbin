#################################################################
#
#   Copyright (c) 2005 Zenoss, Inc. All rights reserved.
#
#################################################################

import time
import types
import threading
import Queue

import transaction

from Acquisition import aq_base

from Products.ZenUtils.Utils import importClass

from Exceptions import *

import logging
log = logging.getLogger("zen.ApplyDataMap")

zenmarker = "__ZENMARKER__"

class ApplyDataMap(object):

    def __init__(self, datacollector=None):
        self.datacollector = datacollector


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
        except (SystemExit, KeyboardInterrupt): raise
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
        if getattr(datamap, "compname", False)==False: return changed
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
                    obj = rel._getOb(objmap.id) 
                    objchange = self._updateObject(obj, objmap)
                    if not changed: changed = objchange
                    relids.remove(objmap.id)
                else:
                    self._createRelObject(device, objmap, rname)
                    changed = True
            elif isinstance(objmap, ZenModelRM):
                log.info("linking object %s to device %s relation %s",
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
        changed = False
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
                    log.info("calling function '%s' with '%s' on "
                               "object %s", attname, value, obj.id)
                    changed = True            
            elif att != value:
                setattr(aq_base(obj), attname, value) 
                log.info("set attribute '%s' to '%s' on object '%s'",
                           attname, value, obj.id)
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
        log.info("adding object %s to relationship %s", remoteObj.id, relname)
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
                device = self.app.unrestrictedTraverse(devpath)
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
