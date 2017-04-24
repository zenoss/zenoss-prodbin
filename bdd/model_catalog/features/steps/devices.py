##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from behave import given, when, then

import pickle
import os

def _load_device_maps(maps_path):
    maps = []
    file_names = os.listdir(maps_path)
    for file_name in file_names:
        path = "{}/{}".format(maps_path, file_name)
        with open(path, "rb") as f:
            maps.append(pickle.load(f))
    return maps

@given('the mock "{device_class}" device with ip "{ip}" is in Zenoss')
def step_impl(context, device_class, ip):
    device = context.zen_context.dmd.Devices.findDeviceByIdOrIp(ip)
    if not device:
        maps = _load_device_maps("./model_catalog/features/data/snmp_device")
        device = context.zen_context.zodb_helper.create_device_from_maps(ip, device_class, maps)
    context.device = device


@when('I search for all the device\'s "{object_type}" in model catalog')
def step_impl(context, object_type):
    object_type = object_type.lower()
    catalog_helper = context.zen_context.model_catalog_helper

    if object_type == "components":
        components = catalog_helper.get_device_components(context.device)
        context.indexed_device_components = components
    elif object_type == "mac addresses":
        device_macs = catalog_helper.get_device_macs(context.device)
        context.indexed_macs = device_macs
    else:
        raise NotImplementedError


@then('I get all the device\'s "{object_type}"')
def step_impl(context, object_type):
    object_type = object_type.lower()
    zodb_helper = context.zen_context.zodb_helper

    if object_type == "components":
        device_components = zodb_helper.get_device_components(context.device)
        assert set(device_components) == set(context.indexed_device_components)
    elif object_type == "mac addresses":
        device_macs = zodb_helper.get_device_macs(context.device)
        assert set(device_macs) == set(context.indexed_macs)
    else:
        raise NotImplementedError

