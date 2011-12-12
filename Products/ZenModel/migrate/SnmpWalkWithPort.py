###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__ = """
Migrate snmpwalk command to specify port in order to perform snmpwalk on
non standard ports.
"""
import Migrate

_IP_WITHOUT_PORT = '${here/manageIp} system'
class SnmpWalkWithPort(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        # snmpwalk
        try:
            snmpwalk = dmd.userCommands._getOb('snmpwalk')
            if _IP_WITHOUT_PORT in snmpwalk.command:
                snmpwalk.command = snmpwalk.command.replace(_IP_WITHOUT_PORT, '${here/manageIp}:${here/zSnmpPort} system', 1)
        except AttributeError:
            pass

SnmpWalkWithPort()

