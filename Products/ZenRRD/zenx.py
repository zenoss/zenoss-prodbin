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
#! /usr/bin/python

__doc__='''zenx.py

Provide sendevent, get config, save perf data, etc services to remote daemons
via xmlrpc.
'''

import time
from sets import Set
import socket

import Globals
from Products.ZenEvents.EventServer import EventServer
#from WebTestConfServer import WebTestConfServer
from Products.ZenEvents.Event import Event

from twisted.internet import reactor, defer
from twisted.python import failure
from twisted.web import xmlrpc, server

XML_RPC_PORT = 8081

class ZenX(EventServer, xmlrpc.XMLRPC):

    totalTime = 0.
    totalEvents = 0
    maxTime = 0.
    name = 'zenx'

    def __init__(self):
        EventServer.__init__(self)
        xmlrpc.XMLRPC.__init__(self, allow_none=True)
        reactor.listenTCP(self.options.xmlrpcport, server.Site(self))

    # Event Server
    
    def execute(self, method, data):
        try:
            d = defer.Deferred()
            self.q.put( (method, data, d, time.time()) )
            return d
        except Exception, ex:
            self.log.exception(ex)

    def xmlrpc_sendEvent(self, data):
        'XMLRPC requests are processed asynchronously in a thread'
        return self.execute(self.sendEvent, (Event(**data),))

    def xmlrpc_sendEvents(self, data):
        return self.execute(self.sendEvents, ([Event(**e) for e in data],))

    def xmlrpc_getDevicePingIssues(self, *unused):
        return self.execute(self.zem.getDevicePingIssues, ())
    
    def xmlrpc_getWmiConnIssues(self, *args):
        return self.execute(self.zem.getWmiConnIssues, args)
        
    def doHandleRequest(self, *args):
        ''' EventServer is calling this in a separate thread to handle
        requests in self.q
        '''
        method, data, result, ts = args
        try:
            retval = method(*data)
            if retval is None:
                retval = ''
            reactor.callFromThread(result.callback, retval)
        except Exception, ex:
            self.log.exception(ex)
            reactor.callFromThread(result.errback,
                                   xmlrpc.Fault(self.FAILURE, str(ex)))
                                   
    # ZenWeb

    def xmlrpc_getPageChecks(self, monitorName=socket.getfqdn()):
        return self.execute(self.getPageChecks, (monitorName,))

    def getPageChecks(self, monitorName=socket.getfqdn()):
        monitor = getattr(self.dmd.Monitors.Performance, monitorName, '')
        if monitor:
            import pprint
            result = monitor.getPageChecks()
            #result = [{'a':1, 'b':2}, {'c':3, 'd':4}]
            #result = ('a', 'b', 'c')
            self.log.info('--------------')
            self.log.info(pprint.pformat(result))
            self.log.info('--------------')
        else:
            raise 'No performance monitor named %s' % monitorName
        return result


    # Misc
    
    def buildOptions(self):
        EventServer.buildOptions(self)
        self.parser.add_option('-x', '--xport',
                               help='Port for xmlrpc.'
                               ' Default is %s' % XML_RPC_PORT,
                               dest='xmlrpcport',
                               type='int',
                               default=XML_RPC_PORT)


if __name__ == '__main__':
    z = ZenX()
    z.main()
