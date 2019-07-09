##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
from collections import defaultdict

from ZODB.transact import transact
from zope.event import notify

import Globals  # noqa. required to import zenoss Products
from Products.ZenUtils.Utils import importClass
from Products.ZenUtils.deprecated import deprecated
from Products.DataCollector.plugins.DataMaps import RelationshipMap, ObjectMap
from Products.ZenModel.ZenModelRM import ZenModelRM

from .incrementalupdate import (
    IncrementalDataMap,
)
from .datamaputils import (
    _locked_from_updates,
    _locked_from_deletion,
)

from .reporter import ADMReporter
from .events import DatamapAddEvent, DatamapProcessedEvent


log = logging.getLogger("zen.ApplyDataMap")
log.setLevel(logging.DEBUG)

CLASSIFIER_CLASS = '/Classifier'

'''TODO: get dmd from utility
from zope.component import getUtility
from Products.Zuul.interfaces import IDataRootFactory
get_dmd = getUtility(IDataRootFactory)
dmd = get_dmd()
'''


def isSameData(x, y):
    """
    A more comprehensive check to see if existing model data is the same as
    newly modeled data. The primary focus is comparing unsorted lists of
    dictionaries.
    """
    if isinstance(x, (tuple, list)) and isinstance(y, (tuple, list)):
        if (
            x and y
            and all(isinstance(i, dict) for i in x)
            and all(isinstance(i, dict) for i in y)
        ):
            x = set(tuple(sorted(d.items())) for d in x)
            y = set(tuple(sorted(d.items())) for d in y)
        else:
            return sorted(x) == sorted(y)

    return x == y


class ApplyDataMap(object):

    def __init__(self, datacollector=None):
        self.datacollector = datacollector
        self.num_obj_changed = 0
        self._dmd = None
        if datacollector:
            self._dmd = getattr(datacollector, 'dmd', None)

        self._reporter = ADMReporter()

    def setDeviceClass(self, device, deviceClass=None):
        """
        If a device class has been passed and the current class is not
        /Classifier then move the device to the newly clssified device class.
        """
        if (
            deviceClass
            and device.getDeviceClassPath().startswith(CLASSIFIER_CLASS)
        ):
            device.changeDeviceClass(deviceClass)

    def applyDataMap(
        self,
        device,
        datamap,
        relname="",
        compname="",
        modname="",
        parentId="",
        commit=True,
    ):
        """Apply a datamap passed as a list of dicts through XML-RPC,
        A RelatinshipMap, or an ObjectMap

        Apply datamap to device. Return True if datamap changed device.

        The default value for commit is True for backwards-compatibility
        reasons. If you're a new caller to ApplyDataMap._applyData you should
        probably set commit to False and handle your own transactions.

        @type device: Device
        @param device: Device to be updated by a RelationshipMap,
            or parent device of an ObjectMap.
        @type datamap: RelationshipMap, ObjectMap
        @param datamap: map used to update the device, and its components
        @return: True if updated, False if not
        """
        log.debug('requested applyDataMap for device=%s', device)
        notify(DatamapAddEvent(self._dmd, datamap, device))
        if not device or _locked_from_updates(device):
            log.warn('device is locked from updates: device=%s', device)
            return False

        datamap = _validate_datamap(
            device,
            datamap,
            relname=relname,
            compname=compname,
            modname=modname,
            parentId=parentId
        )

        # Preprocess datamap, setting directive and diff
        if isinstance(datamap, RelationshipMap):
            datamap = _process_relationshipmap(datamap, device)
            if not datamap:
                return False
            adm_method = self._apply_relationshipmap
        else:
            adm_method = self._apply_incrementalmap

        # apply the changes
        if commit:
            result = transact(adm_method)(datamap, device)
        else:
            result = adm_method(datamap, device)

        # report the changes made
        result = self._report_changes(datamap, device)
        log.debug('applyDataMap result=%s', result)
        return result

    _applyDataMap = applyDataMap  # stop abusing _functions

    def _apply_relationshipmap(self, relmap, device):
        relname = relmap.relname
        log.debug('_apply_relationshipmap to %s.%s', device, relmap.relname)
        # remove any objects no longer included in the relationshipmap
        # to be deleted (device, relationship_name, object/id)
        for obj in relmap._diff['removed']:
            _remove_relationship(relmap._parent, relname, obj)

        # update relationships for each object in the relationship map
        for object_map in relmap:
            if isinstance(object_map, IncrementalDataMap):
                self._apply_incrementalmap(object_map, device)

            elif isinstance(object_map, ZenModelRM):
                # add the relationship to the device
                device.addRelation(relname, object_map)
            else:
                raise RuntimeError(
                    'expected ObjectMap, found %s' % object_map.__class__
                )

    def _apply_incrementalmap(self, incremental_map, device):
        log.debug('_apply_incrementalmap: incremental_map=%s', incremental_map)
        ret = incremental_map.apply()
        notify(DatamapProcessedEvent(
            self._dmd, incremental_map, incremental_map.target
        ))
        return ret

    def stop(self):
        pass

    def _report_changes(self, datamap, device):
        if isinstance(datamap, RelationshipMap):
            self._report_relationshipmap_changes(datamap, device)

            directives = [
                'nochange', 'update', 'add', 'remove', 'rebuild',
                'update_locked', 'delete_locked',
            ]
            counts = {directive: 0 for directive in directives}
            for object_map in datamap:
                counts[object_map._directive] += 1
                self._reporter.report_directive(device, object_map)
            log.info(
                'applied RelationshipMap changes:'
                ' target=%s.%s, change_counts=%s',
                device.id, datamap.relname, counts
            )
            changecount = sum(
                v for k, v in counts.iteritems() if k is not 'nochange'
            )
            changed = bool(changecount or datamap._diff['removed'])

        elif isinstance(datamap, ObjectMap):
            self._report_objectmap_changes(datamap, device)
            changed = (
                True if datamap._directive in ['add', 'update'] else False
            )

        elif isinstance(datamap, IncrementalDataMap):
            self._report_objectmap_changes(datamap, device)
            changed = datamap.changed

        else:
            log.warn('_report_changes for unknown datamap type %s', datamap)
            changed = False

        return changed

    def _report_relationshipmap_changes(self, relmap, device):

        for deleted in relmap._diff['removed']:
            self._reporter.report_removed(
                device, relname=relmap.relname, target=deleted
            )

        for locked in relmap._diff['locked']:
            self._reporter.report_delete_locked(
                device, target=locked, relname=relmap.relname
            )

    def _report_objectmap_changes(self, objectmap, obj):
        self._reporter.report_directive(obj, objectmap)

    @deprecated
    def _updateRelationship(self, device, relmap):
        '''This stub is left to satisfy backwards compatability requirements
        for the monkeypatch in ZenPacks.zenoss.PythonCollector
        ZenPacks/zenoss/PythonCollector/patches/platform.py
        '''
        self.applyDataMap(device=device, datamap=relmap)

    @deprecated
    def _removeRelObject(self, device, objmap, relname):
        '''This stub is left to satisfy backwards compatability requirements
        for the monkeypatch in ZenPacks.zenoss.PythonCollector
        ZenPacks/zenoss/PythonCollector/patches/platform.py
        '''
        pass

    @deprecated
    def _createRelObject(self, device, objmap, relname):
        '''This stub is left to satisfy backwards compatability
        some zenpacks call this method directly
        '''
        objmap.relname = relname
        idm = IncrementalDataMap(device, objmap)
        changed = self.applyDataMap(device=device, datamap=idm)
        return (changed, idm.target)


##############################################################################
# Preproce, diff and set directives
##############################################################################

def _validate_datamap(
    device, datamap, relname=None, compname=None, modname=None, parentId=None
):
    if isinstance(datamap, RelationshipMap):
        log.debug('_validate_datamap: got valid RelationshipMap')
    elif relname:
        log.debug('_validate_datamap: build relationship_map using relname')
        datamap = RelationshipMap(
            relname=relname,
            compname=compname,
            modname=modname,
            objmaps=datamap,
            parentId=parentId
        )
    elif isinstance(datamap, IncrementalDataMap):
        log.debug('_validate_datamap: got valid IncrementalDataMap')
    elif isinstance(datamap, ObjectMap):
        log.debug('_validate_datamap: got valid ObjectMap')
        datamap = IncrementalDataMap(device, datamap)
    else:
        log.debug('_validate_datamap: build object_map')
        datamap = ObjectMap(datamap, compname=compname, modname=modname)
        datamap = IncrementalDataMap(device, datamap)

    return datamap


def _get_relmap_target(device, relmap):
    '''get the device object associated with this map
    returns the object specified in the datamap
    '''
    device = _validate_device_class(device)
    if not device:
        log.debug('_get_relmap_target: no device found')
        return None

    pid = getattr(relmap, "parentId", None)
    if pid:
        if device.id == pid:
            return device
        else:
            return _get_object_by_pid(device, pid)

    path = getattr(relmap, 'compname', None)
    if path:
        return device.getObjByPath(relmap.compname)

    return device


# Used by relmap add
def _get_objmap_target(device, objmap):
    objmap._target = device  # default target is base

    target_path = getattr(objmap, 'compname', None)
    if target_path:
        objmap._target = device.getObjByPath(target_path)

    try:
        relationship = getattr(objmap._target, objmap._relname)
        objmap._target = relationship._getOb(objmap.id)
    except Exception:
        log.warn('_get_objmap_target: Unable to find target object')

    return objmap._target


def _validate_device_class(device):
    '''There's the potential for a device to change device class during
    modeling. Due to this method being run within a retrying @transact,
    this will result in device losing its deviceClass relationship.
    '''
    try:
        if device.deviceClass():
            return device
    except AttributeError:
        pass

    # TODO: expose dmd as a utility in zenhub worker
    new_device = device.dmd.Devices.findDeviceByIdExact(device.id)
    if new_device:
        log.debug(
            "changed device class during modeling: device=%s, class=%s",
            new_device.titleOrId(), new_device.getDeviceClassName()
        )
        return new_device

    log.warning(
        "lost its device class during modeling: device=%s", device.titleOrId()
    )
    return None


def _get_object_by_pid(device, parent_id):
    objects = device.componentSearch(id=parent_id)
    if len(objects) == 1:
        return objects[0].getObject()
    elif len(objects) < 1:
        log.warn('Unable to find a matching parentId: parentID=%s', parent_id)
    else:
        # all components must have a unique ID
        log.warn('too many matches for parentId: parentId=%s', parent_id)
    return None


def _process_relationshipmap(relmap, base_device):
    relname = relmap.relname
    parent = _get_relmap_target(base_device, relmap)
    if parent:
        relmap._parent = parent
    else:
        log.warn('relationship map parent device not found. relmap=%s', relmap)
        return False

    if not hasattr(relmap._parent, relname):
        log.warn(
            'relationship not found: parent=%s, relationship=%s',
            relmap._parent.id, relname,
        )
        return False

    relmap._relname = relname

    seenids = defaultdict(int)
    for object_map in relmap:
        seenids[object_map.id] += 1
        object_map.relname = relname
        if seenids[object_map.id] > 1:
            object_map.id = "%s_%s" % (object_map.id, seenids[object_map.id])

    # remove any objects no longer included in the relationshipmap
    # to be deleted (device, relationship_name, object/id)
    relmap._diff = _get_relationshipmap_diff(relmap._parent, relmap)

    new_maps = [
        _validate_datamap(parent, object_map)
        for object_map in relmap.maps
    ]
    for map in new_maps:
        map.plugin_name = relmap.plugin_name

    relmap.maps = new_maps

    return relmap


def _get_relationshipmap_diff(device, relmap):
    '''Return a list of objects on the device, that are not in the relmap
    '''
    relationship = getattr(device, relmap.relname)
    relids = _get_relationship_ids(device, relmap.relname)
    removed = set(relids) - set([o.id for o in relmap])
    missing_objects = (relationship._getOb(id) for id in removed)

    diff = {'removed': [], 'locked': []}
    for obj in missing_objects:
        if _locked_from_deletion(obj):
            diff['locked'].append(obj)
        else:
            diff['removed'].append(obj)

    return diff


def _get_relationship_ids(device, relationship_name):
    relationship = getattr(device, relationship_name)
    return set(relationship.objectIdsAll())


##############################################################################
# Apply Changes
##############################################################################

def _remove_relationship(parent, relname, obj):
    '''Remove a related object from a parent's relationship

    parent: parent device
    relname: name of the relatinship on device
    object_map: object map for the object to be removed from the relationship
    '''
    try:
        parent.removeRelation(relname, obj)
    except AttributeError:
        return False

    return True


def _create_object(object_map, parent_device=None):
    '''Create a new zodb object from an ObjectMap
    '''
    parent = getattr(object_map, '_parent', None)
    constructor = importClass(object_map.modname, object_map.classname)

    if hasattr(object_map, 'id'):
        new_object = constructor(object_map.id)
    elif parent:
        new_object = constructor(parent, object_map)
    elif parent_device:
        new_object = constructor(parent_device, object_map)
    else:
        log.error('_create_object requires object_map.id or parent_device')
        new_object = None

    return new_object
