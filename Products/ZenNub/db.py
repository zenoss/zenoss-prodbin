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

import logging

from .model import Device, ModelerPlugin, DeviceClass, RRDTemplate, ClassModel
from .config.deviceclasses import load_yaml as load_dc_yaml
from .config.devices import load_yaml as load_device_yaml
from .config.modelerplugins import load_yaml as load_modelerplugin_yaml
from .config.classmodels import load_yaml as load_classmodel_yaml
from .utils import all_parent_dcs
from .mapper import DataMapper

log = logging.getLogger('zen.zennub.db')
_DB = None

# return a singleton for the database
def get_nub_db():
    global _DB
    if _DB is None:
        _DB = DB()
    return _DB


class DB(object):

    def __init__(self):
        self.device_classes = {}
        self.devices = {}
        self.modelerplugin = {}
        self.mappers = {}
        self.classmodel = {}

        # device class -> any device below it in the hierarchy
        self.child_devices = {}

    def load(self):
        # Load the contents of the on-disk YAML files into the db.

        log.info("Loading device classes and monitoring templates..")
        for id_, dc in load_dc_yaml().iteritems():
            dc['deviceClassId'] = id_
            try:
                self.store_deviceclass(DeviceClass(**dc))
            except ValueError, e:
                log.error("Unable to load deviceclass %s: %s", id_, e)

        log.info("Loading devices")
        for id_, d in load_device_yaml().iteritems():
            d['deviceId'] = id_
            try:
                self.store_device(Device(**d))
            except ValueError, e:
                log.error("Unable to load device %s: %s", id_, e)

        log.info("Loading modeler plugin info")
        for id_, d in load_modelerplugin_yaml().iteritems():
            d['pluginId'] = id_
            try:
                self.store_modelerplugin(ModelerPlugin(**d))
            except ValueError, e:
                log.error("Unable to load modelerplugin %s: %s", id_, e)

        log.info("Loading class model")
        for id_, d in load_classmodel_yaml().iteritems():
            d['module'] = id_
            try:
                self.store_classmodel(ClassModel(**d))
            except ValueError, e:
                log.error("Unable to load class model %s: %s", id_, e)

        log.info("Indexing")
        self.index()

        log.info("Loading complete")

    def get_mapper(self, deviceId):
        if deviceId not in self.mappers:
            mapper = DataMapper("zennub")
            log.debug("Creating DataMapper for device %s" % deviceId)
            self.mappers[deviceId] = mapper
            device = mapper.get(deviceId, create_if_missing=True)
            device["type"] = self.devices[deviceId].getProperty("zPythonClass")
            log.debug("  Setting device type to %s" % device["type"])
            mapper.update({deviceId: device})

        return self.mappers[deviceId]

    def store_device(self, device):
        self.devices[device.deviceId] = device

    def store_deviceclass(self, deviceclass):
        self.device_classes[deviceclass.deviceClassId] = deviceclass

    def store_modelerplugin(self, modelerplugin):
        self.modelerplugin[modelerplugin.pluginId] = modelerplugin

    def store_classmodel(self, classmodel):
        self.classmodel[classmodel.module] = classmodel

    def index(self):

        # store a list of devices that are in each device class (or a subclass)
        # creates blank intermediate DCs where needed
        for device in self.devices.values():
            for dc in all_parent_dcs(device.device_class):
                if dc not in self.device_classes:
                    self.store_deviceclass(DeviceClass(deviceClassId=dc))
                self.child_devices.setdefault(dc, [])
                self.child_devices[dc].append(device)



