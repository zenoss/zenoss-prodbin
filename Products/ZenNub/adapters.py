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
import sys

from .db import get_nub_db

_MODULE = None
def get_module():
    global _MODULE
    if _MODULE is not None:
        return _MODULE

    parent_module = importlib.import_module(ZODBishAdapter.__module__)
    module_name = ZODBishAdapter.__module__ + ".adapted"
    module = imp.new_module(module_name)
    module.__name__ = module_name
    sys.modules[module_name] = module
    setattr(parent_module, 'adapted', module)

    _MODULE = importlib.import_module(module_name)
    return _MODULE


class ZODBishAdapter(object):
    def __init__(self, device, datumId, datum):
        self._device = device
        self._datumId = datumId
        self._datum = datum
        db = get_nub_db()
        self._mapper = db.get_mapper(device.id)

        # Create a subclass for each component type, if it doesn't already exist
        try:
            class_name = datum['type'].split('.')[-1]
        except Exception:
            raise ValueError("Unable to determine type for %s" % datumId)
        module = get_module()

        new_class = getattr(module, class_name, None)
        if not new_class:
            class_factory = type(ZODBishAdapter)
            new_class = class_factory(class_name, (ZODBishAdapter,), {})
            new_class.__module__ = module.__name__
            setattr(module, class_name, new_class)

        # Change our class to this subclass.
        self.__class__ = new_class

        # Load the custom subclass with "property" methods that pull the
        # data in from its source.  Doing it this way makes dir, hasattr,
        # etc work normally.

        # id
        self.id = datumId

        # zproperties
        for zProp in device.getAllProperties():
            if hasattr(self, zProp):
                continue
            setattr(self.__class__, zProp, property(lambda self, zProp=zProp: device.getProperty(zProp)))

        # properties
        for prop in datum['properties']:
            if hasattr(self, prop):
                continue
            setattr(self.__class__, prop, property(lambda self, prop=prop: datum['properties'].get(prop)))

        # relationships

        # Install accessor methods for the related objects, wrapping them in
        # ZODBishAdapters as well.
        new_links = set()
        for name in datum['links']:
            if hasattr(self, name):
                continue

            if self._relname_is_tomany(name):
                def ToManyGetter(name=name):
                    return [ ZODBishAdapter(device, dId, self._mapper.get(dId))
                             for dId in datum['links'][name] ]
                setattr(self, name, ToManyGetter)
            else:
                def ToOneGetter(name=name):
                    if len(datum['links'][name]) == 0:
                        return None
                    dId = list(datum['links'][name])[0]
                    return ZODBishAdapter(device, dId, self._mapper.get(dId))
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
                    return ZODBishAdapter(device, dId, self._mapper.get(dId))

                delattr(self, name)
                setattr(self.__class__, name, property(DirectGetter))

    def device(self):
        return ZODBishAdapter(self._device, self._device.id, self._mapper.get(self._device.id))

    def __repr__(self):
        return "<ZODBishAdapter for %s %s of Device %s>" % (self._datum['type'], self._datumId, self._device.id)

    def _relname_is_tomany(self, relname):
        # is the specified relationship (link) a toMany relationship?

        otype = self._mapper.get_object_type(self._datumId)
        ltype = otype.get_link_type(relname)

        if ltype is None:
            raise ValueError("Invalid relname (%s) for %s" % (relname, self._datumId))

        return ltype.local_many
