###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__='''

Set zRouteMapMaxRoutes defaults

$Id:$
'''
import Migrate
import zExceptions

class AddDeviceClassDescriptionAndProtocol(Migrate.Step):
    version = Migrate.Version(2, 4, 0)

    def cutover(self, dmd):

        # Set values for some core organizers
        for path, desc, protocol in [
            ('/Server/Windows', 'Windows Server', 'SNMP'),
            ('/Server/Linux', 'Linux Server', 'SNMP'),
            ('/Network', 'Generic Switch/Router', 'SNMP'),
        ]:
            try:
                org = dmd.Devices.unrestrictedTraverse(path[1:])
            except KeyError:
                pass
            else:
                org.register_devtype(desc, protocol)


AddDeviceClassDescriptionAndProtocol()


class RegisterRootDevtype(Migrate.Step):
    """Register root devtype, to support propertyItems access at all device type levels."""
    version = Migrate.Version(3,1,0)

    def cutover(self, dmd):
        if not dmd.Devices.hasProperty('devtypes'):
            dmd.Devices._setProperty('devtypes', [], 'lines')


RegisterRootDevtype()

