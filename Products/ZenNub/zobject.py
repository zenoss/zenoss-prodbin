##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

# Given a ZenNub device model object and a mapper datum representing that device
# or a component of that device, provide an object that looks more or less
# like what we would store in ZODB, which can be used in place of a Device
# or DeviceComponent.  This isn't meant to be 100%, but it is intended to be
# a minimal functionality for things like zenpython params() methods to execute
# against.

import importlib
import imp
import json
import sys
import types

from Products.ZenUtils.Utils import importClass
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from Products.ZenRelations.RelSchema import ToMany, ToManyCont

from zope.component import getGlobalSiteManager, provideSubscriptionAdapter, provideAdapter
from zope.interface import implementedBy
from ZenPacks.zenoss.Impact.impactd.interfaces import IRelationshipDataProvider
from ZenPacks.zenoss.DynamicView.interfaces import IRelationsProvider, IRelatable

_DMD = None

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
# for use in zennub.
#
# If we find that to be frequently needed, we might consider making this
# more automatic, based on a decorator or naming convention. (foo -> nub_foo
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
            'getWBEMStatsInstanceID': 'getWBEMStatsInstanceID'
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
        datum = self._datum
        isDevice = self._mapper.get_object_type(datumId).device

        # Change our class to a dynamically created subclass that has
        # the right @properties on it.
        self.__class__ =  get_adapted_class(datum['type'], self.__class__)

        # Load the custom subclass with "property" methods that pull the
        # data in from its source.  Doing it this way makes dir, hasattr,
        # etc work normally.

        # id
        self.id = datumId

        # meta_type
        if datum['type'] in db.classmodel:
            setattr(self.__class__, 'meta_type', db.classmodel[datum['type']].meta_type)

        # zproperties
        for zProp in device.getAllProperties():
            if hasattr(self, zProp):
                continue
            setattr(self.__class__, zProp, property(lambda self, zProp=zProp: device.getProperty(zProp)))

        # properties
        propnames = set()
        objtype = self._mapper.get_object_type(self._datumId)
        for prop in [objtype.get_property(p) for p in objtype.properties]:
            propnames.add(prop)
        objtype = self._mapper.get_object_type(self._device.id)
        for prop in [objtype.get_property(p) for p in objtype.properties]:
            propnames.add(prop)

        for prop in propnames:
            if hasattr(self, prop):
                continue

            def PropertyGetter(self, prop=prop):
                if prop in datum['properties']:
                    return datum['properties'].get(prop)
                else:
                    # "acquire" property values from device if they are not
                    # defined on the component.
                    if not isDevice:
                        deviceDatum = self._mapper.get(self._device.id)
                        return deviceDatum['properties'].get(prop, None)

            def PropertySetter(self, v, prop=prop):
                datum['properties'][prop] = v

            setattr(self.__class__, prop, property(PropertyGetter, PropertySetter))

        # relationships

        # Install accessor methods for the related objects, wrapping them in
        # ZDeviceOrComponents as well.
        new_links = set()

        for rel in self._orig_class._relations:
            name = rel[0]
            toMany = isinstance(rel[1], ToMany) or isinstance(rel[1], ToManyCont)

            if hasattr(self, name) or hasattr(self.__class__, name):
                continue

            if toMany:
                def ToManyGetter(name=name):
                    if name not in datum['links']:
                        return []
                    return [ZDeviceComponent(db, device, dId)
                            for dId in datum['links'][name]]
                setattr(self, name, ToManyGetter)
            else:
                def ToOneGetter(name=name):
                    if name not in datum['links']:
                        return None
                    if len(datum['links'][name]) == 0:
                        return None
                    dId = list(datum['links'][name])[0]
                    return ZDeviceComponent(db, device, dId)
                setattr(self, name, ToOneGetter)

            if name in datum['links']:
                new_links.add(name)

        # If we just added 'os' or 'hw' accessor methods to a device,
        # change them out for properties, because those objects are directly
        # contained.
        if isDevice:
            for name in ('os', 'hw', ):
                def DirectGetter(self, name=name):
                    if len(datum['links'][name]) == 0:
                        return None
                    dId = list(datum['links'][name])[0]
                    return ZDeviceComponent(db, device, dId)

                setattr(self.__class__, name, property(DirectGetter))

        # Proxy specific methods to the original wrapped class as specified by METHOD_MAP
        if datum['type'] in METHOD_MAP:
            # Regular methods.  (if necessary, we can add support for classmethod, etc- for now
            # this is all that is supported)

            orig_class = self._orig_class
            if 'method' in METHOD_MAP[datum['type']]:
                for from_method_name, to_method_name in METHOD_MAP[datum['type']]['method'].iteritems():
                    if not hasattr(orig_class, to_method_name):
                        raise ValueError("%s is not a valid method on %s (%s).  Check METHOD_MAP." % (
                            to_method_name, datum['type'], orig_class))
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
        for adapter in gsm.adapters.subscriptions([implementedBy(cls._orig_class)], IRelationshipDataProvider):
            provideSubscriptionAdapter(adapter, [cls], IRelationshipDataProvider)

        # Copy all registered IRelationshipDataProviders and IRelatables (dynamic view) registered for the
        # original zope class over to this adapted version.
        for adapter in gsm.adapters.subscriptions([implementedBy(cls._orig_class)], IRelationsProvider):
            provideSubscriptionAdapter(adapter, [cls], IRelationsProvider)
        adapter = gsm.adapters.lookup([implementedBy(cls._orig_class)], IRelatable)
        if adapter:
            provideAdapter(adapter, [cls], IRelatable)

    def getDmd(self):
        global _DMD
        if _DMD is None:
            _DMD = ZDummyDmd()
        return _DMD

    def getPrimaryId(self):
        return IGlobalIdentifier(self).guid

    def aqBaseHasAttr(self, attrname):
        return hasattr(self, attrname)

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

class ZDummyDmd(object):
    pass

class ZDevice(ZObject):
    def device(self):
        return self


class ZDeviceComponent(ZObject):
    def device(self):
        return ZDevice(self._db, self._device, self._device.id)
