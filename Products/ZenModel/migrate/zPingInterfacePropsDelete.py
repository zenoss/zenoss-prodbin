###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__='''

remove zPingInterfaceName and zPingInterfaceDescription from everything.

'''
import Migrate

class zPingInterfacePropsDelete(Migrate.Step):
    version = Migrate.Version(2, 5, 0)
    
    def cutover(self, dmd):
        orgs = [dmd.Devices]
        orgs.extend(dmd.Devices.getSubOrganizers())
        for org in orgs:
            deleteZProp(org, 'zPingInterfaceName')
            deleteZProp(org, 'zPingInterfaceDescription')
        #now do devices; use generator
        for device in dmd.Devices.getSubDevicesGen():
            deleteZProp(device, 'zPingInterfaceName')
            deleteZProp(device, 'zPingInterfaceDescription')
        
def deleteZProp(obj, zProp):
        if obj.hasProperty(zProp):
            obj.deleteZenProperty(zProp)

zPingInterfacePropsDelete()

