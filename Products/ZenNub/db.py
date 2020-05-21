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
import os
import pickle

from .model import Device, ModelerPlugin, ParserPlugin, DeviceClass, RRDTemplate, ClassModel, DataSource
from .yamlconfig import (
    load_deviceclass_yaml,
    load_device_yaml,
    load_modelerplugin_yaml,
    load_parserplugin_yaml,
    load_classmodel_yaml,
    load_datasource_yaml
)

from .utils import all_parent_dcs
from .mapper import DataMapper
from .zobject import ZDevice, ZDeviceComponent

SNAPSHOT_DIR="/opt/zenoss/etc/nub/snapshot"

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
        self.parserplugin = {}
        self.mappers = {}
        self.classmodel = {}
        self.datasource = {}

        # device class -> any device below it in the hierarchy
        self.child_devices = {}

    def load(self):
        # Load the contents of the on-disk YAML files into the db.

        log.info("Loading device classes and monitoring templates..")
        dc_yaml, mt_yaml = load_deviceclass_yaml()
        for id_, dc in dc_yaml.iteritems():
            dc['id'] = id_
            dc.update(mt_yaml[id_])
            try:
                self.store_deviceclass(DeviceClass(**dc))
            except ValueError, e:
                log.error("Unable to load deviceclass %s: %s", id_, e)

        log.info("Loading devices")
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

        log.info("Loading modeler plugin info")
        for id_, d in load_modelerplugin_yaml().iteritems():
            d['id'] = d['pluginName']
            try:
                self.store_modelerplugin(ModelerPlugin(**d))
            except ValueError, e:
                log.error("Unable to load modelerplugin %s: %s", id_, e)

        log.info("Loading parser plugin info")
        for id_, d in load_parserplugin_yaml().iteritems():
            d['id'] = d['modPath']
            try:
                self.store_parserplugin(ParserPlugin(**d))
            except ValueError, e:
                log.error("Unable to load modelerplugin %s: %s", id_, e)

        log.info("Loading class model")
        for id_, d in load_classmodel_yaml().iteritems():
            d['module'] = id_
            try:
                self.store_classmodel(ClassModel(**d))
            except ValueError, e:
                log.error("Unable to load class model %s: %s", id_, e)

        log.info("Loading datasources")
        for id_, d in load_datasource_yaml().iteritems():
            d['id'] = id_
            try:
                self.store_datasource(DataSource(**d))
            except ValueError, e:
                log.error("Unable to load datasource %s: %s", id_, e)

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
                    return self.mappers[id]
                except Exception, e:
                    log.error("Error reading DataMapper snapshot from %s: %s", filename, e)

            mapper = DataMapper("zennub")
            log.debug("Creating new DataMapper for device %s" % id)
            self.mappers[id] = mapper
            device = mapper.get(id, create_if_missing=True)
            device["type"] = self.devices[id].getProperty("zPythonClass")
            log.debug("  Setting device type to %s" % device["type"])
            mapper.update({id: device})

        return self.mappers[id]

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

    def snapshot_device(self, id):
        if id not in self.mappers:
            log.error("No mapper found for %s", id)
            return

        filename = "%s/%s.pickle" % (SNAPSHOT_DIR, id)
        log.debug("Writing %s", filename)
        with open(filename, "w") as f:
            pickle.dump(self.mappers[id], f)

    def store_device(self, device):
        self.devices[device.id] = device

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
        for device in self.devices.values():
            for dc in all_parent_dcs(device.device_class):
                if dc not in self.device_classes:
                    self.store_deviceclass(DeviceClass(id=dc))
                self.child_devices.setdefault(dc, [])
                self.child_devices[dc].append(device)



