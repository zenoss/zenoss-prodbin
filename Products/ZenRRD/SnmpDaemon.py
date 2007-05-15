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
#! /usr/bin/env python 

__doc__='''SnmpDaemon

Common performance monitoring daemon code for zenperfsnmp and zenprocess.

$Id$
'''

__version__ = "$Revision$"[11:-2]

from RRDDaemon import RRDDaemon

try:
    from pynetsnmp.twistedsnmp import snmpprotocol
except:
    import warnings
    warnings.warn("Using python-based snmp engine")
    from twistedsnmp import snmpprotocol


class SnmpDaemon(RRDDaemon):
    snmpCycleInterval = 5*60            # seconds
    heartBeatTimeout = snmpCycleInterval*3

    properties = RRDDaemon.properties + ('snmpCycleInterval',)
    
    def __init__(self, name):
        RRDDaemon.__init__(self, name)
        self.snmpPort = snmpprotocol.port()
        
    def setPropertyItems(self, items):
        RRDDaemon.setPropertyItems(self, items)
        self.heartBeatTimeout = self.snmpCycleInterval*3
