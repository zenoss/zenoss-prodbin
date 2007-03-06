#! /usr/bin/env python 
#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''SnmpDaemon

Common performance monitoring daemon code for zenperfsnmp and zenprocess.

$Id$
'''

__version__ = "$Revision$"[11:-2]

from RRDDaemon import RRDDaemon

try:
    from pynetsnmp.twistedsnmp import snmpprotocol
except:
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
