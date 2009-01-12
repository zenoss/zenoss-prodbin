#! /usr/bin/env python 
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

DEFAULT_HTTP_PORT = 8091

import Globals

from Products.ZenHub.PBDaemon import PBDaemon
from RenderServer import RenderServer as OrigRenderServer
from Products.ZenUtils.ObjectCache import ObjectCache

from twisted.web import resource, server
from twisted.internet import reactor

import mimetypes

class RenderServer(OrigRenderServer):

    cache = None

    def setupCache(self):
        """make new cache if we need one"""
        if self.cache is None:
            self.cache = ObjectCache()
            self.cache.initCache()
        return self.cache

class HttpRender(resource.Resource):

    isLeaf = True

    def render_GET(self, request):
        args = request.args.copy()
        for k, v in args.items():
            if len(v) == 1:
                args[k] = v[0]
        command = request.postpath[-1]
        zr.log.debug("Processing %s request" % command)
        args.setdefault('ftype', 'PNG')
        ftype = args['ftype']
        del args['ftype']
        mimetype = mimetypes.guess_type('.%s'%ftype)[0]
        if not mimetype: mimetype = 'image/%s'%ftype
        request.setHeader('Content-type', mimetype)
        return getattr(zr, 'remote_' + command)(**args)

class zenrender(PBDaemon):

    initialServices = ['EventService', 'ZenRender']
    name = 'zenrender'

    def __init__(self):
        PBDaemon.__init__(self)
        self.rs = RenderServer(self.name)
    
    def connected(self):
        if self.options.cycle:
            self.heartbeat()
    
    def heartbeat(self):
        reactor.callLater(self.heartbeatTimeout / 3, self.heartbeat)
        PBDaemon.heartbeat(self)

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

    def buildOptions(self):
        PBDaemon.buildOptions(self)
        self.parser.add_option('--http-port',
                               dest='httpport',
                               default=DEFAULT_HTTP_PORT,
                               help='Port zenrender listens on for http'
                               'render requests.  Default is %s.' %
                               DEFAULT_HTTP_PORT)


if __name__ == '__main__':
    zr = zenrender()
    reactor.listenTCP(int(zr.options.httpport), server.Site(HttpRender()))
    zr.run()
