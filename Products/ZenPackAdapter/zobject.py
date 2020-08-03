##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

# Given a ZenPackAdapter device model object and a mapper datum representing that device
# or a component of that device, provide an object that looks more or less
# like what we would store in ZODB, which can be used in place of a Device
# or DeviceComponent.  This isn't meant to be 100%, but it is intended to be
# a minimal functionality for things like zenpython params() methods to execute
# against.

import importlib
import imp
import json
import logging
import sys
import types

from DateTime import DateTime
from Products.ZenUtils import Time

from Products.ZenUtils.Utils import importClass, monkeypatch
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from Products.ZenRelations.RelSchema import ToMany, ToManyCont

from zope.component import getGlobalSiteManager, provideSubscriptionAdapter, provideAdapter
from zope.interface import implementedBy
from ZenPacks.zenoss.Impact.impactd.interfaces import IRelationshipDataProvider
from ZenPacks.zenoss.DynamicView.interfaces import IRelationsProvider, IRelatable

from .utils import all_parent_dcs

_DMD = None
log = logging.getLogger("zen.cloudpublisher")


# Normally, the adapted versions of components only contain relationships,
# modeled properties, and zProperties.
#
# In some cases, specific methods are also needed for use in tales expressions
# or params() methods.
#
# Generally we can't just call arbitrary methods on the original classes and
# expect them to work outside of zope/zodb.  However, we will support a way to
# do it in a more controlled manner, but explicitly whitelisting methods here.
#
# For each mapped method, the key is the method name on the adapted class
# exposed to tales expressions and params, and the value is the method
# name to call on the original class.   Only methods that can work in this
# context (that is, no dependency on anything other than relationships,
# model properties, and zproperties) can be used this way.   If the method
# relies on being a real zenoss component (ZODB, acquisition, etc), it can't
# work here.  Instead, a new version of the method would have to be written
# for use in ZenPackAdapter.
#
# If we find that to be frequently needed, we might consider making this
# more automatic, based on a decorator or naming convention. (foo -> zpa_foo
# for example

METHOD_MAP = {
    'ZenPacks.zenoss.EMC.base.SMISProvider': {
        'method': {
            'getMonitoringIDs': 'getMonitoringIDs',
            'setMonitoringIDs': 'setMonitoringIDs',
            'getMonitoringIDs': 'getMonitoringIDs'
        }
    },
    'ZenPacks.zenoss.EMC.base.Array': {
        'method': {
            'getWBEMStatsInstanceID': 'getWBEMStatsInstanceID'
        }
    },
    'ZenPacks.zenoss.EMC.base.HardDisk': {
        'method': {
            'getWBEMStatsInstanceID': 'getWBEMStatsInstanceID'
        }
    },
    'ZenPacks.zenoss.EMC.base.LUN': {
        'method': {
            'getWBEMStatsInstanceID': 'getWBEMStatsInstanceID',
             'getInitiators': lambda x: []
        }
    },
    'ZenPacks.zenoss.EMC.base.SP': {
        'method': {
            'getWBEMStatsInstanceID': 'getWBEMStatsInstanceID'
        }
    },
    'ZenPacks.zenoss.EMC.base.SPPort': {
        'method': {
            'getWBEMStatsInstanceID': 'getWBEMStatsInstanceID'
        }
    },
    'ZenPacks.zenoss.NetAppMonitor.NetAppPort': {
        'method': {
            'setParentPorts': 'setParentPorts',
            'getParentPorts': 'getParentPorts',
            'parent_port': 'parent_port',
            'child_port': 'child_port'
        }
    },
    'ZenPacks.zenoss.NetAppMonitor.FileSystem': {
        'method': {
            'getBackingStore': 'getBackingStore'
        }
    },
    'ZenPacks.zenoss.NetAppMonitor.LUN': {
        'method': {
            'getBackingStore': 'getBackingStore'
        }
    }
}


def get_submodule(parent_module, new_module_name):
    if hasattr(parent_module, new_module_name):
        return getattr(parent_module, new_module_name)

    module_name = parent_module.__name__ + "." + new_module_name

    module = imp.new_module(new_module_name)
    module.__name__ = module_name

    sys.modules[module_name] = module
    setattr(parent_module, new_module_name, module)

    return module

def adapted_base_module():
    base_module = importlib.import_module(ZObject.__module__)
    return get_submodule(base_module, "adapted")

def get_adapted_class(typename, zobject_cls):
    class_name = typename.split('.')[-1]
    adapted_modname = ZObject.__module__ + ".adapted."
    adapted_modname += ".".join(typename.split('.')[0:-2])

    module = adapted_base_module()
    for modname in typename.split('.')[0:-2]:
        module = get_submodule(module, modname)

    module = importlib.import_module(adapted_modname)

    adapted_class = getattr(module, class_name, None)
    if not adapted_class:
        class_factory = type(zobject_cls)
        adapted_class = class_factory(class_name, (zobject_cls,), {})
        adapted_class.__module__ = module.__name__
        setattr(module, class_name, adapted_class)

        # Store a reference to the original zenoss type that this adapter is
        # replicating.
        adapted_class._orig_class = importClass(typename)

        # And do any other one-time initialization
        adapted_class.__cls_init__()

    return adapted_class


class ZObject(object):
    _orig_class = None

    def __init__(self, db, device, datumId):
        global METHOD_MAP
        self._db = db
        self._device = device
        self._datumId = datumId
        mawp = db.get_mapper(device.id)
        self._mapper = mawp
        self._datum = self._mapper.get(datumId)
        self._datumType = self._datum['type']
        isDevice = self._mapper.get_object_type(datumId).device

        # Change our class to a dynamically created subclass that has
        # the right @properties on it.
        self.__class__ =  get_adapted_class(self._datumType, self.__class__)

        # Load the custom subclass with "property" methods that pull the
        # data in from its source.  Doing it this way makes dir, hasattr,
        # etc work normally.

        # id
        self.id = datumId

        # meta_type
        if self._datumType in db.classmodel:
            setattr(self.__class__, 'meta_type', db.classmodel[self._datumType].meta_type)

        # collectors (where applicable)
        if hasattr(self._orig_class, 'collectors'):
            setattr(self.__class__, 'collectors', self._orig_class.collectors)

        # dynamicview_relations (where applicable)
        if hasattr(self._orig_class, 'dynamicview_relations'):
            setattr(self.__class__, 'dynamicview_relations', self._orig_class.dynamicview_relations)

        # add device_class and manageIp if it's a device.
        if isDevice:
            setattr(self.__class__, 'device_class', device.device_class)

            def ManageIpGetter(self):
                return device.manageIp

            def ManageIpSetter(self, v):
                device.manageIp = v

            setattr(self.__class__, 'manageIp', property(ManageIpGetter, ManageIpSetter))

        # zproperties
        for zProp in device.getAllProperties():
            if hasattr(self, zProp):
                continue
            def ZPropertyGetter(self, zProp=zProp):
                return self._device.getProperty(zProp)

            setattr(self.__class__, zProp, property(ZPropertyGetter, None))

        # properties
        propnames = set()
        objtype = self._mapper.get_object_type(self._datumId)
        for prop in objtype.properties:
            propnames.add(objtype.get_property(prop) or prop)
        objtype = self._mapper.get_object_type(self._device.id)
        for prop in objtype.properties:
            propnames.add(objtype.get_property(prop) or prop)

        for prop in propnames:
            if hasattr(self, prop) or prop == 'title':
                continue

            def PropertyGetter(self, prop=prop):
                if prop in self._datum['properties']:
                    return self._datum['properties'].get(prop)
                else:
                    # "acquire" property values from device if they are not
                    # defined on the component.
                    if not isDevice:
                        deviceDatum = self._mapper.get(self._device.id)
                        return deviceDatum['properties'].get(prop, None)

            def PropertySetter(self, v, prop=prop):
                self._datum['properties'][prop] = v

            setattr(self.__class__, prop, property(PropertyGetter, PropertySetter))

        # title
        def TitleGetter(self):
            return self._datum['title']

        def TitleSetter(self, v):
            self._datum['title'] = v
        setattr(self.__class__, 'title', property(TitleGetter, TitleSetter))

        # relationships

        # Install accessor methods for the related objects, wrapping them in
        # ZDeviceOrComponents as well.
        new_links = set()

        for rel in self._orig_class._relations:
            name = rel[0]
            toMany = isinstance(rel[1], ToMany) or isinstance(rel[1], ToManyCont)

            if hasattr(self, name) or hasattr(self.__class__, name):
                continue

            zrel = ZRelationship(self, name, toMany)
            setattr(self, name, zrel)

            if name in self._datum['links']:
                new_links.add(name)

        # If we just added 'os' or 'hw' accessor methods to a device,
        # change them out for properties, because those objects are directly
        # contained.
        if isDevice:
            for name in ('os', 'hw', ):
                def DirectGetter(self, name=name):
                    if len(self._datum['links'][name]) == 0:
                        return None
                    dId = list(self._datum['links'][name])[0]
                    return ZDeviceComponent(db, device, dId)

                setattr(self.__class__, name, property(DirectGetter))

        # Proxy specific methods to the original wrapped class as specified by METHOD_MAP
        if self._datumType in METHOD_MAP:
            # Regular methods.  (if necessary, we can add support for classmethod, etc- for now
            # this is all that is supported)
            orig_class = self._orig_class
            if 'method' in METHOD_MAP[self._datumType]:
                for from_method_name, to_method_name in METHOD_MAP[self._datumType]['method'].iteritems():

                    # if the value is callable, hook it in.
                    if callable(to_method_name):
                        to_func = to_method_name
                        setattr(self.__class__, from_method_name, types.MethodType(to_func, self, self.__class__))
                        continue

                    # otherwise, it should be a method on the target class.
                    if not hasattr(orig_class, to_method_name):
                        raise ValueError("%s is not a valid method on %s (%s).  Check METHOD_MAP." % (
                            to_method_name, self._datumType, orig_class))
                    to_method = getattr(orig_class, to_method_name)
                    to_func = to_method.__func__
                    setattr(self.__class__, from_method_name, types.MethodType(to_func, self, self.__class__))

    @classmethod
    def __cls_init__(cls):
        # called when each ZObject subclass is created- one-time
        # initialization steps can happen here.

        gsm = getGlobalSiteManager()

        # Copy all registered IRelationshipDataProviders (impact) registered for the
        # original zope class over to this adapted version.
        log.debug("Copying impact adapters from %s to %s", cls._orig_class, cls)
        for adapter in gsm.adapters.subscriptions([implementedBy(cls._orig_class)], IRelationshipDataProvider):
            log.debug("provideSubscriptionAdapter(%s, [%s], IRelationshipDataProvider)", adapter, cls)
            provideSubscriptionAdapter(adapter, [cls], IRelationshipDataProvider)

        # Copy all registered IRelationshipDataProviders and IRelatables (dynamic view) registered for the
        # original zope class over to this adapted version.
        for adapter in gsm.adapters.subscriptions([implementedBy(cls._orig_class)], IRelationsProvider):
            @monkeypatch(adapter)
            def relations(self, **kwargs):
                try:
                    for relation in original(self, **kwargs):
                        yield relation
                except Exception, e:
                    log.error("Error processing %s impact adapter: %s", adapter, e)

            log.debug("provideSubscriptionAdapter(%s, [%s], IRelationsProvider)", adapter, cls)
            provideSubscriptionAdapter(adapter, [cls], IRelationsProvider)
        adapter = gsm.adapters.lookup([implementedBy(cls._orig_class)], IRelatable)
        if adapter:
            log.debug("provideAdapter(%s, [%s], IRelatable)", adapter, cls)
            provideAdapter(adapter, [cls], IRelatable)

    def titleOrId(self):
        return getattr(self, 'title', self.id)

    def getDmd(self):
        global _DMD
        if _DMD is None:
            _DMD = ZDummyDmd()
        return _DMD

    def getPrimaryId(self):
        return IGlobalIdentifier(self).guid

    def aqBaseHasAttr(self, attrname):
        return hasattr(self, attrname)

    def propertyIds(self):
        return sorted(self._datum['properties'])

    def getProperty(self, id, d=None):
        if id in self._datum['properties']:
            return self._datum['properties'][id]
        return d

    def __repr__(self):
        return "<%s for %s %s of Device %s>" % (
            self.__class__.__name__,
            self._datum['type'],
            self._datumId,
            self._device.id
        )

    def rrdPath(self):
        return json.dumps(self.getMetricMetadata(), sort_keys=True)

    def getMetricMetadata(self, dev=None):
        if dev is None:
            dev = self.device()

        return {
            'type': 'METRIC_DATA',

            'deviceId': dev.id,
            'contextId': self.id,
            'deviceUUID': dev.id,
            'contextUUID': self.id,
            'contextKey': self.id
        }

    def dimensions(self):
        dimensions = {
            'device': self._device.id,
            'component': self._datumId
        }
        if dimensions['component'] == dimensions['device']:
            del dimensions['component']

        return dimensions

    def getSubComponents(self):
        isDevice = self._mapper.get_object_type(self._datumId).device
        directly_contained = []

        if isDevice:
            if self.os:
                directly_contained.append(self.os)
            if self.hw:
                directly_contained.append(self.hw)

        for rel in self._orig_class._relations:
            if isinstance(rel[1], ToManyCont):
                for contained_component in getattr(self, rel[0])():
                    directly_contained.append(contained_component)

        for component in directly_contained:
            yield component

            for subcomponent in component.getSubComponents():
                yield subcomponent

class ZDummyDmd(object):
    pass


class ZRelationship(object):
    def __init__(self, parent_object, relname, toMany=False):
        self.parent_object = parent_object
        self.relname = relname
        self.toMany = toMany

    def __call__(self):
        datum = self.parent_object._datum
        db = self.parent_object._db
        device = self.parent_object._device

        if self.toMany:
            if self.relname not in datum['links']:
                return []
            return [ZDeviceComponent(db, device, dId)
                    for dId in datum['links'][self.relname]]
        else:
            if self.relname not in datum['links']:
                return None
            if len(datum['links'][self.relname]) == 0:
                return None
            dId = list(datum['links'][self.relname])[0]
            return ZDeviceComponent(db, device, dId)

    def __repr__(self):
        cardinality = "toOne"
        if self.toMany:
            cardinality = "toMany"
        return "<%s relationship %s for %s %s of Device %s>" % (
            cardinality,
            self.relname,
            self.parent_object._datum['type'],
            self.parent_object._datumId,
            self.parent_object._device.id
        )


    def _getOb(self, _id):
        if _id in self.parent_object._datum['links'][self.relname]:
            return ZDeviceComponent(self.parent_object._db, self.parent_object._device, _id)
        else:
            raise AttributeError(_id)


class ZDeviceOrComponent(ZObject):
    def getRRDTemplates(self):
        clsname = self._datum["type"]
        if clsname not in self._db.classmodel:
            log.error("Unable to locate monitoring templates for components of unrecognized class %s", clsname)
            return []

        rrdTemplateName = self._db.classmodel[clsname].default_rrd_template_name
        seen = set()
        templates = []

        for dc in all_parent_dcs(self.device().device_class):
            for template_name, template in self._db.device_classes[dc].rrdTemplates.iteritems():
                if template_name in seen:
                    # lower level templates with the same name take precendence
                    continue
                seen.add(template_name)

                # this really should use getRRDTemplateName per instance,
                # but that is not available to us without zodb.   So we
                # use a single value that was determined by update_zenpacks.py
                if template_name == rrdTemplateName:
                    templates.append(template)

        return templates

    def getMonitoredComponents(self, collector=None):
        # should filter based on monitored status, but we don't have
        # such a thing.  So just return all components.
        for component in self.getSubComponents():
            if collector is not None:
                if collector in getattr(component, 'collectors', []):
                    yield component
            else:
                yield component

    def snmpIgnore(self):
        # Ignore interface that are administratively down.
        if hasattr(self, "adminStatus"):
            return self.adminStatus > 1

        return False


class ZDevice(ZDeviceOrComponent):
    def device(self):
        return self

    def getDeviceComponents(self, collector=None):
        for component in self.getSubComponents():
            if collector is not None:
                if collector in getattr(component, 'collectors', []):
                    yield component
            else:
                yield component

    def getLastChange(self):
        return DateTime(float(self._device._lastChange))

    def getLastChangeString(self):
        return Time.LocalDateTimeSecsResolution(float(self._device._lastChange))

class ZDeviceComponent(ZDeviceOrComponent):
    def device(self):
        return ZDevice(self._db, self._device, self._device.id)


