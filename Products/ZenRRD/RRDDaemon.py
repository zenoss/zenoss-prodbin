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

__doc__='''RRDDaemon

Common performance monitoring daemon code for performance daemons.

$Id$
'''

__version__ = "$Revision$"[11:-2]

import socket

import Globals
from Products.ZenEvents import Event
from Products.ZenEvents.ZenEventClasses import Perf_Snmp, Heartbeat
from Products.ZenUtils.Driver import drive

from twisted.internet import reactor, defer
from twisted.python import failure

from Products.ZenHub.PBDaemon import FakeRemote, PBDaemon as Base
from Products.ZenRRD.ThresholdManager import ThresholdManager, Threshold

BAD_SEVERITY=Event.Warning

BASE_URL = 'http://localhost:8080/zport/dmd'
DEFAULT_URL = BASE_URL + '/Monitors/Performance/localhost'


COMMON_EVENT_INFO = {
    'manager': socket.getfqdn(),
    }
    

class RRDDaemon(Base):
    'Holds the code common to performance gathering daemons.'

    heartbeatevt = {'eventClass':Heartbeat}
    
    properties = ('configCycleInterval',)
    heartBeatTimeout = 60
    configCycleInterval = 20            # minutes
    rrd = None
    shutdown = False

    def __init__(self, name):
        self.events = []
        Base.__init__(self)
        self.name = name
        evt = self.heartbeatevt.copy()
        self.heartbeatevt.update(dict(component=name,
                                      device=socket.getfqdn()))

    def getDevicePingIssues(self):
        return self.eventService().callRemote('getDevicePingIssues')

    def remote_setPropertyItems(self, items):
        self.log.debug("Async update of collection properties")
        self.setPropertyItems(items)


    def remote_updateDeviceList(self, devices):
        self.log.debug("Async update of device list")


    def setPropertyItems(self, items):
        'extract configuration elements used by this server'
        table = dict(items)
        for name in self.properties:
            value = table.get(name, None)
            if value is not None:
                if getattr(self, name) != value:
                    self.log.debug('Updated %s config to %s' % (name, value))
                setattr(self, name, value)


    def sendThresholdEvent(self, **kw):
        "Send the right event class for threshhold events"
        self.sendEvent({}, **kw)

    def heartbeat(self, *unused):
        'if cycling, send a heartbeat, else, shutdown'
        if not self.options.cycle:
            self.stop()
            return
        self.sendEvent(self.heartbeatevt, timeout=self.heartBeatTimeout*3)


    def buildOptions(self):
        Base.buildOptions(self)
        self.parser.add_option('-d', '--device',
                               dest='device',
                               default='',
                               help="Specify a specific device to monitor")

    def logError(self, msg, error):
        if isinstance(error, failure.Failure):
            self.log.exception(error)
        else:
            self.log.error('%s %s', msg, error)

    def error(self, error):
        'Log an error, including any traceback data for a failure Exception'
        self.logError('Error', error)
        if not self.options.cycle:
            self.stop()

    def errorStop(self, why):
        self.error(why)
        self.stop()

    def model(self):
        return self.services.get(self.initialServices[-1], FakeRemote())

