###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__ = """
This makes all of the user commands run on the collector of the
device.
This also sets the commands for Ping and SNMPWalk to work
for both Ipv6 and Ipv4
"""
import Migrate


class CollectorIpv6Commands(Migrate.Step):
    version = Migrate.Version(3, 1, 70)

    def cutover(self, dmd):
        # ping ipv6
        try:
            ping = dmd.userCommands._getOb('ping')
            ping.command = "ucping -c2 ${device/manageIp}"
        except AttributeError:
            pass

        # traceroute
        try:
            traceroute = dmd.userCommands._getOb('traceroute')
            traceroute.command = "uctraceroute -q 1 -w 2 ${device/manageIp}"
        except AttributeError:
            pass

        # snmpwalk
        try:
            snmpwalk = dmd.userCommands._getOb('snmpwalk')
            snmpwalk.command = "snmpwalk -${device/zSnmpVer} -c${device/zSnmpCommunity} ${device/snmpwalkPrefix}${here/manageIp} system"
        except AttributeError:
            pass

        # make all of the default commands work over different collectors
        commands = ['ping', 'traceroute',
                    'DNS forward',
                    'DNS reverse',
                    'snmpwalk']
        for commandName in commands:
            try:
                cmd = dmd.userCommands._getOb(commandName)
                if not cmd.command.startswith('dcsh'):
                    cmd.command = 'dcsh --collector=${device/getPerformanceServerName} "%s"' % (cmd.command)
            except AttributeError:
                pass


CollectorIpv6Commands()
