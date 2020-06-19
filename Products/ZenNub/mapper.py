##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018-2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""Generic modeling support."""

# Default Exports
__all__ = [
    "DataMapper",
]

# stdlib Imports
import collections

# Zenoss Imports
from Products.DataCollector.plugins.DataMaps import ObjectMap, RelationshipMap
from Products.ZenModel.Device import Device
from Products.ZenModel.OperatingSystem import OperatingSystem
from Products.ZenModel.DeviceHW import DeviceHW
from Products.ZenRelations.RelSchema import ToManyCont, ToOne
from Products.ZenUtils.Utils import importClass

# Public Classes

class DataMapper(object):
    plugin_name = None

    # Public Methods

    def __init__(self, plugin_name):
        self.plugin_name = plugin_name
        self.object_types = {}
        self.objects = {}
        self.delayed = {}
        self.delayed_oms = []
        self.objects_by_type = collections.defaultdict(set)

        # This value is increased whenever a structural change is
        # made to the graph- adding or removing objects or links between
        # them.  It will not change if a property is modified.
        self.schemaversion = 0

    def add(self, object_id, datum):
        if object_id not in self.objects:
            self.schemaversion += 1

        obj = self.stub(object_id)

        object_type = self.get_object_type(object_id, datum)
        if not object_type:
            raise Exception("no type specified for %s", object_id)

        obj["type"] = object_type.name
        self.objects_by_type[object_type.name].add(object_id)

        if "title" in datum:
            obj["title"] = datum["title"]

        if "properties" in datum:
            for prop_name, prop_value in datum["properties"].iteritems():
                self.add_property(
                    object_id,
                    object_type,
                    prop_name,
                    prop_value)

        if "links" in datum:
            for link_name, remote_ids in datum["links"].iteritems():
                self.add_link(
                    object_id,
                    object_type,
                    link_name,
                    remote_ids)
        if "delay" in datum:
            # Delayed data are typically set_* methods that have to execute
            # after initial objects are created. Once identified, the delayed
            # data will be removed from the existing maps and added in a
            # new ObjectMap at the end of the datamaps.

            delay_data = {'delayed': datum.get('delay'),
                          'modname': datum.get('type')}

            self.delayed.update({object_id: delay_data})

    def update(self, data):
        for object_id, datum in data.iteritems():
            self.add(object_id, datum)

    def extend(self, data):
        for object_id, datum in data:
            self.add(object_id, datum)

    def remove(self, object_id):
        datum = self.objects.get(object_id)
        if datum is None:
            return

        object_type = self.get_object_type(object_id)
        if object_type:
            self.objects_by_type[object_type.name].discard(object_id)

            for link_name, remote_ids in datum["links"].iteritems():
                self.remove_link(
                    object_id,
                    object_type,
                    link_name,
                    remote_ids)

        self.objects.pop(object_id)
        self.schemaversion += 1

    def by_type(self, type_name):
        for object_id in list(self.objects_by_type.get(type_name, ())):
            yield object_id, self.objects[object_id]

    def all(self):
        for object_id in list(self.objects):
            yield object_id, self.objects[object_id]

    def get(self, object_id, create_if_missing=False):
        if create_if_missing:
            return self.stub(object_id)
        else:
            if object_id in self.objects:
                return self.objects.get(object_id)
            else:
                return None



    # Private Methods

    def stub(self, object_id):
        if object_id not in self.objects:
            self.objects[object_id] = {
                "type": None,
                "title": None,
                "properties": {},
                "links": collections.defaultdict(set)}

        return self.objects[object_id]

    def add_property(self, object_id, object_type, name, value):
        object_property = object_type.get_property(name)
        if not object_property:
            print("invalid property name for {}: {}".format(object_id, name))
            # raise Exception(
            #     "invalid property name for {}: {}".format(
            #         object_id, name))

        # TODO: Property type checking? Automatic coercion?
        self.objects[object_id]["properties"][name] = value

    def add_link(self, object_id, object_type, link_name, remote_ids):
        link_type = object_type.get_link_type(link_name)
        if not link_type:
            raise Exception(
                "invalid link name for {}: {}".format(
                    object_id, link_name))

        if remote_ids is None:
            remote_ids = []
        elif isinstance(remote_ids, basestring):
            remote_ids = [remote_ids]

        local_links = self.objects[object_id]["links"]

        # bump the schemaversion if the links are changed
        if set(local_links[link_type.local_name]) != set(remote_ids):
            self.schemaversion += 1

        local_links[link_type.local_name].update(remote_ids)

        if not link_type.local_many:
            local_link = local_links[link_type.local_name]
            if len(local_link) > 1:
                raise Exception(
                    "too many items in to-one {} relationship for {}: {}"
                    .format(
                        link_type.local_name,
                        object_id,
                        local_link))

        for remote_id in remote_ids:
            remote_links = self.stub(remote_id)["links"]
            remote_links[link_type.remote_name].add(object_id)

            if not link_type.remote_many:
                remote_link = remote_links[link_type.remote_name]
                if len(remote_link) > 1:
                    raise Exception(
                        "too many items in to-one {} relationship for {}: {}"
                        .format(
                            link_type.remote_name,
                            remote_id,
                            remote_link))

    def remove_link(self, object_id, object_type, link_name, remote_ids):
        if not remote_ids:
            return

        link_type = object_type.get_link_type(link_name)
        if not link_type:
            return

        # bump the schemaversion, since we're removing a link.
        self.schemaversion += 1

        remote_name = link_type.remote_name
        for remote_id in list(remote_ids):
            if link_type.local_containing:
                self.remove(remote_id)
            else:
                self.objects[remote_id]["links"][remote_name].remove(object_id)

    def get_object_type(self, object_id, datum=None):
        type_name = datum.get("type") if datum else None

        if not type_name:
            type_name = self.objects.get(object_id, {}).get("type")

        if not type_name:
            return

        if type_name not in self.object_types:
            self.object_types[type_name] = ObjectType(type_name)

        return self.object_types[type_name]


# Private Classes

class ObjectType(object):
    name = None
    device = None
    properties = None
    link_types = None

    def __init__(self, name):
        self.name = name

        class_ = importClass(name)

        self.device = issubclass(class_, Device)

        self.properties = {
            x["id"]
            for x in class_._properties}

        # special metadata for zenoss cloud
        self.properties.add('impactFromDimensions')
        self.properties.add('impactToDimensions')

        self.link_types = {
            k: LinkType(k, v)
            for k, v in class_._relations}

        if self.device:

            # Figure out what type the os and hw relationships should be
            # (supporting patching of these objects with subclasses, by
            # __init__, as is done in some zenpacks such as StorageBase
            # and EMC.base)
            o = class_('dummy')
            os_class = o.os.__module__
            hw_class = o.hw.__module__

            if not issubclass(o.os.__class__, OperatingSystem):
                raise Exception("%s: os object is not a subclass of OperatingSystem" % self.name)
            if not issubclass(o.hw.__class__, DeviceHW):
                raise Exception("%s: os object is not a subclass of OperatingSystem" % self.name)

            self.link_types['os'] = LinkType('os', ToOne(ToOne, os_class, "device"))
            self.link_types['hw'] = LinkType('hw', ToOne(ToOne, hw_class, "device"))
            self.link_types['os'].local_containing = True
            self.link_types['hw'].local_containing = True

        if issubclass(class_, OperatingSystem):
            self.link_types['device'] = LinkType('device', ToOne(ToOne, "Products.ZenModel.Device", "os"))

        if issubclass(class_, DeviceHW):
            self.link_types['device'] = LinkType('device', ToOne(ToOne, "Products.ZenModel.Device", "hw"))

    def get_property(self, name):
        if 'set_' in name:
            name = name.replace('set_', '')

        if name in self.properties:
            return name

    def get_link_type(self, name):
        return self.link_types.get(name)


class LinkType(object):
    local_name = None
    remote_name = None
    remote_class = None
    local_containing = None
    remote_containing = None
    local_many = None
    remote_many = None

    def __init__(self, name, relschema):
        self.local_name = name
        self.remote_name = relschema.remoteName
        self.remote_class = relschema.remoteClass

        if isinstance(relschema, ToManyCont):
            self.local_containing = True
        else:
            self.local_containing = False

        if issubclass(relschema.remoteType, ToManyCont):
            self.remote_containing = True
        else:
            self.remote_containing = False

        if isinstance(relschema, ToOne):
            self.local_many = False
        else:
            self.local_many = True

        if issubclass(relschema.remoteType, ToOne):
            self.remote_many = False
        else:
            self.remote_many = True
