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

ORGANIZERS_FACT_PLUGIN = 'zen_organizers'
DEVICE_INFO_FACT_PLUGIN = 'zen_device_info'
DELETION_FACT_PLUGIN = 'zen_deletion'


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
    PROD_STATE_KEY = "prod_state"
    DELETED_KEY = "deleted"


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

    def set_context_uuid_from_object(self, obj):
        self.metadata[FactKeys.CONTEXT_UUID_KEY] = get_context_uuid(obj)

    def set_meta_type_from_object(self, obj):
        self.metadata[FactKeys.META_TYPE_KEY] = obj.meta_type


def get_context_uuid(obj):
    uuid = ""
    try:
        uuid = obj.getUUID()
    except Exception:
        pass
    return uuid


def deletion_fact(obj_uuid):
    f = Fact()
    f.metadata[FactKeys.CONTEXT_UUID_KEY] = obj_uuid
    f.metadata[FactKeys.PLUGIN_KEY] = DELETION_FACT_PLUGIN
    f.data[FactKeys.DELETED_KEY] = True
    return f


def device_info_fact(device):
    """
    Given a device, generates its device info fact
    """
    f = Fact()
    f.set_context_uuid_from_object(device)
    f.set_meta_type_from_object(device)
    f.metadata[FactKeys.PLUGIN_KEY] = DEVICE_INFO_FACT_PLUGIN
    f.data[FactKeys.NAME_KEY] = device.titleOrId()
    f.data[FactKeys.PROD_STATE_KEY] = device.getProductionStateString()
    return f


def organizer_fact_from_device(device):
    """
    Given a device, generates its organizers fact
    """
    device_fact = Fact()
    device_fact.set_context_uuid_from_object(device)
    device_fact.set_meta_type_from_object(device)
    device_fact.metadata[FactKeys.PLUGIN_KEY] = ORGANIZERS_FACT_PLUGIN
    device_fact.data[FactKeys.DEVICE_CLASS_KEY] = device.getDeviceClassName()
    device_fact.data[FactKeys.LOCATION_KEY] = device.getLocationName()
    device_fact.data[FactKeys.SYSTEMS_KEY] = device.getSystemNames()
    device_fact.data[FactKeys.GROUPS_KEY] = device.getDeviceGroupNames()
    return device_fact


def organizer_fact_from_device_component(device_fact, comp_uuid, comp_meta_type):
    """
    Given a device component, generates its organizers fact
    @param device_fact: organizers fact for device
    """
    comp_fact = copy.deepcopy(device_fact)
    comp_fact.metadata[FactKeys.CONTEXT_UUID_KEY] = comp_uuid
    comp_fact.metadata[FactKeys.META_TYPE_KEY] = comp_meta_type
    comp_fact.id = shortid()
    return comp_fact

'''
def organizer_facts_for_device(device, include_components=True):
    """
    Given a device generate facts containing all the organizers (device class, systems,
    groups, locations) the device and its components belong to
    @param device: device for which its organizers facts are requested
    @param include_components: whether to include organizers facts for the device's components
    @return: generator with the organizers facts for the device and its components(if required)
    """
    device_fact = organizer_fact_from_device(device)
    if device_fact.is_valid():
        yield device_fact
        if include_components:
            for comp_brain in device.componentSearch(query={}):
                if not comp_brain.getUUID:
                    continue
                comp_fact = organizer_fact_from_device_component(device_fact, comp_brain.getUUID, comp_brain.meta_type)
                if comp_fact.is_valid():
                    yield comp_fact


def organizer_facts_for_devices(devices, include_components=True):
    """
    @param devices_uuids: uuids of the devices for which we want to generate organizer facts
    @return: generator with organizers facts for all devices and their components (if required)
    """
    gen_list = []
    for device in devices:
        if not device:
            continue
        fgen = organizer_facts_for_device(device, include_components)
        gen_list.append(fgen)
    return chain(*gen_list)
'''

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

