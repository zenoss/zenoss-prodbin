##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


# In-memory database holding all devices, device classes, and monitoring
# templates.

import datetime
import logging
import os
import pickle
import re
import time

from zope.component import getUtility
from zope.event import notify

from Products.ZenHub.server import IHubServerConfig

from .model import Device, ModelerPlugin, ParserPlugin, DeviceClass, RRDTemplate, ClassModel, DataSource
from .yamlconfig import (
    load_deviceclass_yaml,
    load_device_yaml,
    load_modelerplugin_yaml,
    load_parserplugin_yaml,
    load_classmodel_yaml,
    load_datasource_yaml,
    DEVICE_YAML,
)

from .utils import all_parent_dcs, datetime_millis
from .mapper import DataMapper
from .zobject import ZDevice, ZDeviceComponent
from .cloudpublisher import CloudModelPublisher, sanitize_field
from .modelevents import ZenPackAdapterDeletedDeviceEvent, ZenPackAdapterAddedDeviceEvent, ZenPackAdapterUpdatedDeviceEvent


SNAPSHOT_DIR="/data/snapshot"

log = logging.getLogger('zen.zenpackadapter.db')
_DB = None


# return a singleton for the database
def get_db():
    global _DB
    if _DB is None:
        _DB = DB()
    return _DB


class DB(object):

    def __init__(self):
        self.device_classes = {}
        self.devices = {}
        self.modelerplugin = {}
        self.parserplugin = {}
        self.mappers = {}
        self.classmodel = {}
        self.datasource = {}

        # device class -> any device below it in the hierarchy
        self.child_devices = {}

        # The model publisher (set with set_model_publisher before using)
        self.model_publisher = None

    def load(self):
        # create snapshot directory if it is missing
        if not os.path.exists(SNAPSHOT_DIR):
            os.mkdir(SNAPSHOT_DIR)

        # Load the contents of the on-disk YAML files into the db.
        self.load_deviceclasses()
        self.load_devices()
        self.load_modelerplugins()
        self.load_parserplugins()
        self.load_classmodels()
        self.load_datasources()

        log.info("Indexing")
        self.index()

        log.info("Loading complete")

    def load_deviceclasses(self):
        log.info("Loading device classes and monitoring templates..")
        dc_yaml, mt_yaml = load_deviceclass_yaml()
        for id_, dc in dc_yaml.iteritems():
            dc['id'] = id_
            dc.update(mt_yaml[id_])
            try:
                self.store_deviceclass(DeviceClass(**dc))
            except ValueError, e:
                log.error("Unable to load deviceclass %s: %s", id_, e)

    def load_devices(self):
        log.info("Loading devices")

        # The devices.yaml file is written out by zdatamon.  If it doesn't exist
        # yet, wait for it.
        while not os.path.exists(DEVICE_YAML):
            log.info("  waiting for %s" % DEVICE_YAML)
            time.sleep(3)

        for id_, d in load_device_yaml().iteritems():
            d['id'] = id_
            try:
                self.store_device(Device(**d))
            except ValueError, e:
                log.error("Unable to load device %s: %s", id_, e)

            # quick check for unnecessary zProp settings in devices.yaml
            # that could be removed.
            if id_ in self.devices:
                for zProp, value in self.devices[id_].zProperties.iteritems():
                    if self.devices[id_].getPropertyDefault(zProp) == value:
                        print "   Note: device %s zProperty %s is already its default" % (id_, zProp)

    def load_modelerplugins(self):
        log.info("Loading modeler plugin info")
        for id_, d in load_modelerplugin_yaml().iteritems():
            d['id'] = d['pluginName']
            try:
                self.store_modelerplugin(ModelerPlugin(**d))
            except ValueError, e:
                log.error("Unable to load modelerplugin %s: %s", id_, e)

    def load_parserplugins(self):
        log.info("Loading parser plugin info")
        for id_, d in load_parserplugin_yaml().iteritems():
            d['id'] = d['modPath']
            try:
                self.store_parserplugin(ParserPlugin(**d))
            except ValueError, e:
                log.error("Unable to load modelerplugin %s: %s", id_, e)

    def load_classmodels(self):
        log.info("Loading class model")
        for id_, d in load_classmodel_yaml().iteritems():
            d['module'] = id_
            try:
                self.store_classmodel(ClassModel(**d))
            except ValueError, e:
                log.error("Unable to load class model %s: %s", id_, e)

    def load_datasources(self):
        log.info("Loading datasources")
        for id_, d in load_datasource_yaml().iteritems():
            d['id'] = id_
            try:
                self.store_datasource(DataSource(**d))
            except ValueError, e:
                log.error("Unable to load datasource %s: %s", id_, e)

    def reload_devices(self):
        log.info("Reloading %s", DEVICE_YAML)
        while not os.path.exists(DEVICE_YAML):
            log.info("  waiting for %s" % DEVICE_YAML)
            time.sleep(3)

        device_yaml = load_device_yaml()

        old_devices = set(self.devices.keys())
        new_devices = set(device_yaml.keys())

        for deviceId in old_devices - new_devices:
            notify(ZenPackAdapterDeletedDeviceEvent(deviceId))
            self.delete_device(deviceId)

        for deviceId in new_devices - old_devices:
            notify(ZenPackAdapterAddedDeviceEvent(deviceId))

        changed_devices = set()

        for id_, d in device_yaml.iteritems():
            d['id'] = id_
            try:
                if self.store_device(Device(**d)):
                    changed_devices.add(id_)
            except ValueError, e:
                log.error("Unable to reload device %s: %s", id_, e)

        for deviceId in changed_devices:
            notify(ZenPackAdapterUpdatedDeviceEvent(deviceId))

        log.info("Indexing")
        self.index()

        log.info("Loading complete")

    def get_mapper(self, id):
        if id not in self.mappers:
            filename = "%s/%s.pickle" % (SNAPSHOT_DIR, id)
            if os.path.exists(filename):
                try:
                    log.debug("Reading DataMapper for device %s from last snapshot.", id)
                    with open(filename, "r") as f:
                        self.mappers[id] = pickle.load(f)

                    # Clear out stored schema, in case it's changed and is
                    # no longer compatible.  It will be recreated as necessary
                    self.mappers[id].object_types = {}

                    self._ensure_mapper_os_hw(id, self.mappers[id])
                    return self.mappers[id]
                except Exception, e:
                    log.error("Error reading DataMapper snapshot from %s: %s", filename, e)

            mapper = DataMapper("zenpackadapter")
            log.debug("Creating new DataMapper for device %s" % id)
            self.mappers[id] = mapper
            device = mapper.get(id, create_if_missing=True)
            device["type"] = self.devices[id].getProperty("zPythonClass")
            log.debug("  Setting device type to %s" % device["type"])
            mapper.update({id: device})

        self._ensure_mapper_os_hw(id, self.mappers[id])
        return self.mappers[id]

    def _ensure_mapper_os_hw(self, id, mapper):
        object_type = mapper.get_object_type(id)

        # create 'os' and 'hw' components if they are missing
        os_datum = mapper.get('os', create_if_missing=True)
        hw_datum = mapper.get('hw', create_if_missing=True)

        added = False
        if os_datum["type"] is None:
            os_type = object_type.get_link_type('os').remote_class
            os_datum["type"] = os_type
            mapper.update({'os': os_datum})
            added = True
        if hw_datum["type"] is None:
            hw_type = object_type.get_link_type('hw').remote_class
            hw_datum["type"] = hw_type
            mapper.update({'hw': hw_datum})
            added = True

        if added:
            device = mapper.get(id)
            device["links"]['os'] = set(["os"])
            device["links"]['hw'] = set(["hw"])
            mapper.update({id: device})


    def get_zobject(self, device=None, component=None):
        # return a ZDevice or ZDeviceComponent based on a set of dimensions
        # (device and component)
        if device not in self.devices:
            return None

        mapper = self.get_mapper(device)

        if component is None or component == device:
            return ZDevice(self, self.devices[device], device)

        if mapper.get(component) is None:
            return None

        return ZDeviceComponent(self, self.devices[device], component)

    def snapshot(self):
        for id in self.mappers:
            self.snapshot_device(id)

        # Also clean up any old leftover snapshot files.
        for file in os.listdir(SNAPSHOT_DIR):
            if file.endswith(".pickle"):
                deviceId = re.sub(r".pickle$", "", file)
                if deviceId not in self.devices:
                    self.delete_device_snapshot(deviceId)

    def snapshot_device(self, id):
        if id not in self.mappers:
            log.error("No mapper found for %s", id)
            return

        filename = "%s/%s.pickle" % (SNAPSHOT_DIR, id)
        log.debug("Writing %s", filename)
        with open(filename, "w") as f:
            pickle.dump(self.mappers[id], f)

    def delete_device_snapshot(self, deviceId):
        filename = "%s/%s.pickle" % (SNAPSHOT_DIR, id)
        if os.path.exists(filename):
            log.info("Removing device snapshot for %s", deviceId)
            os.remove(filename)

    def store_device(self, device):
        if device.id in self.devices:
            if device != self.devices[device.id]:
                self.devices[device.id] = device
                return True
        else:
            self.devices[device.id] = device
            return True

        # no change
        return False

    def delete_device(self, deviceId):
        log.info("Removing device %s" % deviceId)

        mapper = self.get_mapper(deviceId)
        mapper.remove(deviceId)
        self.publish_model(device=deviceId)
        del self.devices[deviceId]
        del self.mappers[deviceId]
        self.delete_device_snapshot(deviceId)

    def store_deviceclass(self, deviceclass):
        self.device_classes[deviceclass.id] = deviceclass

    def store_modelerplugin(self, modelerplugin):
        self.modelerplugin[modelerplugin.id] = modelerplugin

    def store_parserplugin(self, parserplugin):
        self.parserplugin[parserplugin.id] = parserplugin

    def store_classmodel(self, classmodel):
        self.classmodel[classmodel.module] = classmodel

    def store_datasource(self, datasource):
        self.datasource[datasource.id] = datasource

    def index(self):

        # store a list of devices that are in each device class (or a subclass)
        # creates blank intermediate DCs where needed
        self.child_devices = {}
        for device in self.devices.values():
            for dc in all_parent_dcs(device.device_class):
                if dc not in self.device_classes:
                    self.store_deviceclass(DeviceClass(id=dc))
                self.child_devices.setdefault(dc, [])
                self.child_devices[dc].append(device)

    def set_model_publisher(self, publisher):
        self.model_publisher = publisher

    def publish_model(self, device=None, component=None):
        if self.model_publisher is None:
            raise Exception("publish_model can not be called before set_model_publisher")

        mapper = self.get_mapper(device)
        model = {
            'timestamp': datetime_millis(datetime.datetime.utcnow()),
            'dimensions': {
                'device': device,
                'component': component,
                'source': self.model_publisher._source
            },
            'metadataFields': {
                'source-type': "zenoss.zenpackadapter"
            }
        }

        if component is None or component == device:
            datum = mapper.get(device)
            if datum is not None:
                datum['title'] = device
        else:
            datum = mapper.get(component)

        mdf = model['metadataFields']

        if datum is None:
            # Need to delete the component.
            mdf['_zen_deleted_entity'] = True
        else:
            # Otherwise, update it.
            mdf['name'] = sanitize_field(datum['title'])
            try:
                mdf['type'] = sanitize_field(self.classmodel[datum['type']].meta_type)
            except Exception:
                mdf['type'] = sanitize_field(datum['type'])

            for k, v in datum['properties'].iteritems():
                mdf[k] = sanitize_field(v)

            # Add source dimension to impact relationships
            for i, _ in enumerate(mdf.get('impactFromDimensions', [])):
                mdf['impactFromDimensions'][i] += ",source=" + model['dimensions']['source']
            for i, _ in enumerate(mdf.get('impactToDimensions', [])):
                mdf['impactToDimensions'][i] += ",source=" + model['dimensions']['source']

        self.model_publisher.put(model)

