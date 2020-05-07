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

from .db import get_nub_db

_MODULE = None


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


def get_module():
    global _MODULE
    if _MODULE is not None:
        return _MODULE

    parent_module = importlib.import_module(ZManagedObject.__module__)
    module_name = ZManagedObject.__module__ + ".adapted"
    module = imp.new_module(module_name)
    module.__name__ = module_name
    sys.modules[module_name] = module
    setattr(parent_module, 'adapted', module)

    _MODULE = importlib.import_module(module_name)
    return _MODULE


class ZManagedObject(object):
    def __init__(self, device, datumId, datum):
        global METHOD_MAP

        self._device = device
        self._datumId = datumId
        self._datum = datum

        db = get_nub_db()
        self._mapper = db.get_mapper(device.id)
        isDevice = self._mapper.get_object_type(datumId).device

        # Create a subclass for each component type, if it doesn't already exist
        try:
            class_name = datum['type'].split('.')[-1]
        except Exception:
            raise ValueError("Unable to determine type for %s" % datumId)
        module = get_module()

        new_class = getattr(module, class_name, None)
        if not new_class:
            class_factory = type(self.__class__)
            new_class = class_factory(class_name, (self.__class__,), {})
            new_class.__module__ = module.__name__
            setattr(module, class_name, new_class)

        # Change our class to this subclass.
        self.__class__ = new_class

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
        for name in datum['links']:
            if hasattr(self, name):
                continue

            if self._relname_is_tomany(name):
                def ToManyGetter(name=name):
                    return [ZDeviceComponent(device, dId, self._mapper.get(dId))
                            for dId in datum['links'][name]]
                setattr(self, name, ToManyGetter)
            else:
                def ToOneGetter(name=name):
                    if len(datum['links'][name]) == 0:
                        return None
                    dId = list(datum['links'][name])[0]
                    return ZDeviceComponent(device, dId, self._mapper.get(dId))
                setattr(self, name, ToOneGetter)
            new_links.add(name)

        # If we just added 'os' or 'hw' accessor methods to a device,
        # change them out for properties, because those objects are directly
        # contained.
        if self._mapper.get_object_type(datumId).device:
            for name in ('os', 'hw', ):
                if name not in new_links:
                    continue

                def DirectGetter(self, name=name):
                    if len(datum['links'][name]) == 0:
                        return None
                    dId = list(datum['links'][name])[0]
                    return ZDeviceComponent(device, dId, self._mapper.get(dId))

                delattr(self, name)
                setattr(self.__class__, name, property(DirectGetter))

        # Proxy specific methods to the original wrapped class as specified by METHOD_MAP
        if datum['type'] in METHOD_MAP:
            orig_class = importClass(datum['type'])

            # Regular methods.  (if necessary, we can add support for classmethod, etc- for now
            # this is all that is supported)
            if 'method' in METHOD_MAP[datum['type']]:
                for from_method_name, to_method_name in METHOD_MAP[datum['type']]['method'].iteritems():
                    to_method = getattr(orig_class, to_method_name)
                    if to_method is None:
                        raise ValueError("%s is not a valid method on %s.  Check METHOD_MAP." % (
                            to_method, datum['type']))
                    to_func = to_method.__func__
                    setattr(self.__class__, from_method_name, types.MethodType(to_func, self, self.__class__))

    def _relname_is_tomany(self, relname):
        # is the specified relationship (link) a toMany relationship?

        otype = self._mapper.get_object_type(self._datumId)
        ltype = otype.get_link_type(relname)

        if ltype is None:
            raise ValueError("Invalid relname (%s) for %s" % (relname, self._datumId))

        return ltype.local_many

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


class ZDevice(ZManagedObject):
    def device(self):
        return self


class ZDeviceComponent(ZManagedObject):
    def device(self):
        return ZDevice(self._device, self._device.id, self._mapper.get(self._device.id))
