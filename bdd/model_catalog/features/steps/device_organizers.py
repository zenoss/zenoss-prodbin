##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from behave import given, when, then

def _get_devices_path(devices):
    paths = set()
    for device in devices:
        paths.add("/".join(device.getPrimaryPath()))
    return paths    

@when('I search for all devices in "{device_organizer_path}" using getSubDevices')
def step_impl(context, device_organizer_path):
    context.device_organizer = context.zen_context.dmd.unrestrictedTraverse(str(device_organizer_path))
    context.device_organizer_GetSubdevices = _get_devices_path(context.device_organizer.getSubDevices())

@then('I get all the devices available in "{device_organizer_path}"')
def step_impl(context, device_organizer_path):
    devices = _get_devices_path(context.device_organizer.getSubDevices_recursive())
    assert devices == context.device_organizer_GetSubdevices
    