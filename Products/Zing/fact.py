##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

from .shortid import shortid

from json import JSONEncoder
from itertools import chain
import copy
import time
import logging

logging.basicConfig()
log = logging.getLogger("zen.zing")

class FactKeys(object):
    CONTEXT_UUID_KEY = "contextUUID"
    META_TYPE_KEY = "meta_type"
    PLUGIN_KEY = "plugin"
    NAME_KEY = "name"
    MEM_CAPACITY_KEY = "mem_capacity"
    LOCATION_KEY = "location"
    DEVICE_CLASS_KEY = "device_class"
    GROUPS_KEY = "groups"
    SYSTEMS_KEY = "systems"


class Fact(object):
    def __init__(self, f_id=None):
        if not f_id:
            f_id = shortid()
        self.id = f_id
        self.metadata = {}
        self.data = {}

    def update(self, other):
        self.data.update(other)

    def is_valid(self):
        return self.metadata.get(FactKeys.CONTEXT_UUID_KEY) is not None

"""
Given a device, generates its organizers fact
"""
def organizer_fact_from_device(device):
    device_fact = Fact()
    try:
        device_fact.metadata[FactKeys.CONTEXT_UUID_KEY] = device.getUUID()
    except Exception:
        pass
    if hasattr(device, "meta_type"):
        device_fact.metadata[FactKeys.META_TYPE_KEY] = device.meta_type
    device_fact.metadata[FactKeys.PLUGIN_KEY] = 'zen_organizers'
    if hasattr(device, "getDeviceClassName"):
        device_fact.data[FactKeys.DEVICE_CLASS_KEY] = device.getDeviceClassName()
    if hasattr(device, "getLocationName") and device.getLocationName():
        device_fact.data[FactKeys.LOCATION_KEY] = device.getLocationName()
    if hasattr(device, "getSystemNames") and device.getSystemNames():
        device_fact.data[FactKeys.SYSTEMS_KEY] = device.getSystemNames()
    if hasattr(device, "getDeviceGroupNames") and device.getDeviceGroupNames():
        device_fact.data[FactKeys.GROUPS_KEY] = device.getDeviceGroupNames()
    return device_fact


"""
Given a device component, generates its organizers fact
@param device_fact: organizers fact for device
"""
def organizer_fact_from_device_component(device_fact, comp_uuid, comp_meta_type):
    comp_fact = copy.deepcopy(device_fact)
    comp_fact.metadata[FactKeys.CONTEXT_UUID_KEY] = comp_uuid
    comp_fact.metadata[FactKeys.META_TYPE_KEY] = comp_meta_type
    comp_fact.id = shortid()
    return comp_fact


"""
Given a device generate facts containing all the organizers (device class, systems,
groups, locations) the device and its components belong to
@param device: device for which its organizers facts are requested
@param include_components: whether to include organizers facts for the device's components
@return: generator with the organizers facts for the device and its components(if required)
"""
def organizer_facts_for_device(device, include_components=True):
    device_fact = organizer_fact_from_device(device)
    if device_fact.is_valid:
        yield device_fact
        if include_components:
            for comp_brain in device.componentSearch(query={}):
                if not comp_brain.getUUID:
                    continue
                comp_fact = organizer_fact_from_device_component(device_fact, comp_brain.getUUID, comp_brain.meta_type)
                if comp_fact.is_valid:
                    yield comp_fact


"""
@param devices_uuids: uuids of the devices for which we want to generate organizer facts
@return: generator with organizers facts for all devices and their components (if required)
"""
def organizer_facts_for_devices(devices, include_components=True):
    gen_list = []
    for device in devices:
        if not device:
            continue
        fgen = organizer_facts_for_device(device, include_components)
        gen_list.append(fgen)
    return chain(*gen_list)


class _FactEncoder(JSONEncoder):

    def _tweak_data(self, data_in):
        data_out = {}
        for k, v in data_in.iteritems():
            if isinstance(v, list) or isinstance(v, tuple) or isinstance(v, set):
                # whatever comes in the list, set etc. needs to be scalar, if it isnt
                # cast it to string for now.
                # TODO: Review if we need to support more complex types (list of lists, etc)
                values = []
                for x in v:
                    if not isinstance(x, (str, int, long, float, bool)):
                        log.debug("Found non scalar type in list ({}). Casting it to str".format(x.__class__))
                        x = str(x)
                    values.append(x)
                data_out[k] = sorted(values)
            else:
                data_out[k] = [v]
        return data_out

    def default(self, o):
        if isinstance(o, Fact):
            return {
                "id": o.id,
                "data": self._tweak_data(o.data),
                "metadata": o.metadata,
                "timestamp": int(time.time())
            }
        return JSONEncoder.default(self, o)


FactEncoder = _FactEncoder()


def serialize_facts(facts):
    if facts:
        encoded = FactEncoder.encode({"models": facts})
        return encoded

