#! /usr/bin/env python 
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2011 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__ = """zenrender

Listens in order to process RRD files to generate graphs
or retrieve data from a remote collector.
"""

import logging
log = logging.getLogger("zen.zenrender")

import mimetypes
import xmlrpclib

import Globals
import zope.interface

from twisted.web import resource, server
from twisted.internet import reactor

from Products.ZenCollector.daemon import CollectorDaemon
from Products.ZenCollector.interfaces import ICollectorPreferences,\
                                             ITaskSplitter,\
                                             ICollector
from Products.ZenCollector.tasks import NullTaskSplitter

from RenderServer import RenderServer as OrigRenderServer
from Products.ZenUtils.ObjectCache import ObjectCache


class RenderServer(OrigRenderServer):
    cache = None

    def setupCache(self):
        """make new cache if we need one"""
        if self.cache is None:
            self.cache = ObjectCache()
            self.cache.initCache()
        return self.cache


class ZenRenderPreferences(object):
    zope.interface.implements(ICollectorPreferences)
   
    def __init__(self):
        """
        Constructs a new preferences instance and
        provides default values for needed attributes.
        """
        self.collectorName = "zenrender"
        self.configCycleInterval = 20 # minutes
        self.cycleInterval = 5 * 60 # seconds
        self.configurationService = 'Products.ZenHub.services.RenderConfig'
        
        # Will be filled in based on buildOptions
        self.options = None

    def buildOptions(self, parser):
        # Remove device option
        parser.remove_option('--device')
        
        # Add options
        parser.add_option('--http-port', type='int',
                          dest='httpport',
                          default= 8091,
                          help='Port zenrender listens on for HTTP'
                          'render requests. Default is %default.')

    def postStartup(self):
        """ 
        Listen for HTTP requests for RRD data or graphs.
        """
        self._daemon = zope.component.getUtility(ICollector)
        self.log = log
        self.rs = RenderServer(self.collectorName)
       
        # Hookup render methods to self._daemon
        self._daemon.remote_render = self.remote_render
        self._daemon.remote_packageRRDFiles = self.remote_packageRRDFiles
        self._daemon.remote_unpackageRRDFiles = self.remote_unpackageRRDFiles
        self._daemon.remote_receiveRRDFiles = self.remote_receiveRRDFiles
        self._daemon.remote_sendRRDFiles = self.remote_sendRRDFiles
        self._daemon.remote_moveRRDFiles = self.remote_moveRRDFiles
        self._daemon.remote_plugin = self.remote_plugin
        self._daemon.remote_summary = self.remote_summary
        self._daemon.remote_fetchValues = self.remote_fetchValues
        self._daemon.remote_currentValues = self.remote_currentValues
        
        # Start listening for HTTP requests
        httpPort = self. _daemon.options.httpport
        self.log.info("Starting Render Webserver on port %s", httpPort)
        reactor.listenTCP(httpPort, server.Site(HttpRender()))

    def remote_render(self, *args, **kw):
        return self.rs.render(*args, **kw)

    def remote_packageRRDFiles(self, *args, **kw):
        return self.rs.packageRRDFiles(*args, **kw)

    def remote_unpackageRRDFiles(self, *args, **kw):
        return self.rs.unpackageRRDFiles(*args, **kw)

    def remote_receiveRRDFiles(self, *args, **kw):
        return self.rs.receiveRRDFiles(*args, **kw)

    def remote_sendRRDFiles(self, *args, **kw):
        return self.rs.sendRRDFiles(*args, **kw)

    def remote_moveRRDFiles(self, *args, **kw):
        return self.rs.moveRRDFiles(*args, **kw)

    def remote_plugin(self, *args, **kw):
        return self.rs.plugin(*args, **kw)

    def remote_summary(self, *args, **kw):
        return self.rs.summary(*args, **kw)

    def remote_fetchValues(self, *args, **kw):
        return self.rs.fetchValues(*args, **kw)

    def remote_currentValues(self, *args, **kw):
        return self.rs.currentValues(*args, **kw)


class HttpRender(resource.Resource):
    isLeaf = True

    def __init__(self):
        self.log = log
        self._daemon = zope.component.getUtility(ICollector)

    def render_GET(self,request):
        args = request.args.copy()
        for k, v in args.items():
            if len(v) == 1:
                args[k] = v[0]
        command = request.postpath[-1]
        self.log.debug("Processing %s request from %s" , command,request.getClientIP())
        args.setdefault('ftype', 'PNG')
        ftype = args['ftype']
        del args['ftype']
        mimetype = mimetypes.guess_type('x.%s' % ftype)[0]
        if mimetype is None:
            mimetype = 'image/%s' % ftype.lower()
        request.setHeader('Content-type', mimetype)
        return getattr(self._daemon, 'remote_' + command)(**args)

    def render_POST(self, request):
        """
        Deal with XML-RPC requests
        """
        content = request.content.read()
        args, command = xmlrpclib.loads(content)
        self.log.debug("Processing %s request from %s" % (command,request.getClientIP()))
        request.setHeader('Content-type', 'text/xml')
        result = getattr(self._daemon, 'remote_' + command)(*args)
        response = xmlrpclib.dumps((result,),
            methodresponse=True, allow_none=True)
        return response


if __name__ == '__main__':
    myPreferences = ZenRenderPreferences()
    myTaskSplitter = NullTaskSplitter()
    daemon = CollectorDaemon(myPreferences, myTaskSplitter)
    daemon.run()
