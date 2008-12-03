###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """SnmpDaemon

Common performance monitoring daemon code for zenperfsnmp and zenprocess.

"""

from RRDDaemon import RRDDaemon

from pynetsnmp.twistedsnmp import snmpprotocol

class SnmpDaemon(RRDDaemon):
    snmpCycleInterval = 5*60            # seconds
    heartbeatTimeout = snmpCycleInterval*3

    properties = RRDDaemon.properties + ('snmpCycleInterval',)
    
    def __init__(self, name, noopts=False):
        """
        Initializer for common SNMP daemon classes

        @param name: name of the daemon
        @type name: string
        @param noopts: process command-line arguments?
        @type noopts: boolean
        """
        RRDDaemon.__init__(self, name, noopts)
        self.snmpPort = snmpprotocol.port()
        
    def setPropertyItems(self, items):
        """
        Set all of the specified zProperties.

        @param items: kwargs
        @type items: list
        """
        RRDDaemon.setPropertyItems(self, items)
        self.heartbeatTimeout = self.snmpCycleInterval*3
