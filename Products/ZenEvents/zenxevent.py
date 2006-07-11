#! /usr/bin/env python 
#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''zenxevent

Creates events from xml rpc calls.

$Id$
'''

__version__ = "$Revision$"[11:-2]

import time

from EventServer import EventServer
from Event import Event

from twisted.internet import reactor, defer
from twisted.python import failure
from twisted.web import xmlrpc, server

XML_RPC_PORT = 8081

class ZenXEvent(EventServer, xmlrpc.XMLRPC):
    'Listen for xmlrpc requests and turn them into events'

    totalTime = 0.
    totalEvents = 0
    maxTime = 0.
    name = 'zenxevent'

    def __init__(self):
        EventServer.__init__(self)
        xmlrpc.XMLRPC.__init__(self)
        
        reactor.listenTCP(self.options.xmlrpcport, server.Site(self))


    def execute(self, method, data):
        try:
            d = defer.Deferred()
            self.q.put( (method, data, d, time.time()) )
            return d
        except Exception, ex:
            self.log.exception(ex)

    def xmlrpc_sendEvent(self, data):
        'XMLRPC requests are processed asynchronously in a thread'
        return self.execute(self.zem.sendEvent, (Event(**data),))

    def xmlrpc_sendEvents(self, data):
        return self.execute(self.zem.sendEvents, ([Event(**e) for e in data],))

    def xmlrpc_getDevicePingIssues(self, *unused):
        return self.execute(self.zem.getDevicePingIssues, ())
    
    def doHandleRequest(self, *args):
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


    def buildOptions(self):
        EventServer.buildOptions(self)
        self.parser.add_option('--xport',
                               '-x',
                               dest='xmlrpcport',
                               type='int',
                               default=XML_RPC_PORT)
        

if __name__ == '__main__':
    z = ZenXEvent()
    z.main()
