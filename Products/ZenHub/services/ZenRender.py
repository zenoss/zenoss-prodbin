#! /usr/bin/env python 
#################################################################
#
#   Copyright (c) 2007 Zenoss, Inc. All rights reserved.
#
#################################################################

from Products.ZenHub.HubService import HubService
from twisted.web import resource, server
from twisted.internet import reactor

import xmlrpclib

htmlResource = None

import logging
log = logging.getLogger("zenrender")

__doc__ = "Provide a simple web server to forward render requests"

class Render(resource.Resource):

    isLeaf = True

    def __init__(self):
        resource.Resource.__init__(self)
        self.renderers = {}


    def render_GET(self, request):
        "Deal with http requests"
        args = request.args.copy()
        for k, v in args.items():
            if len(v) == 1:
                args[k] = v[0]
        for instance, renderer in self.renderers.items():
            for listener in renderer.listeners:
                try:
                    command = request.postpath[-1]
                    args.setdefault('ftype', 'PNG')
                    ftype = args['ftype']
                    del args['ftype']
                    request.setHeader('Content-type', 'image/%s' % ftype)
                    def write(result):
                        if result:
                            request.write(result)
                        request.finish()
                    def error(reason):
                        log.error("Unable to fetch graph: %s", reason)
                        request.finish()
                    d = listener.callRemote(command, **args)
                    d.addCallbacks(write, error)
                    return server.NOT_DONE_YET
                except Exception, ex:
                    log.exception(ex)
                    log.warning("Skipping renderer %s" % instance)
        raise Exception("No renderer registered")

    def render_POST(self, request):
        "Deal with XML-RPC requests"
        for instance, renderer in self.renderers.items():
            for listener in renderer.listeners:
                try:
                    args, command = xmlrpclib.loads(request.content.read())
                    request.setHeader('Content-type', 'text/xml')
                    d = listener.callRemote(str(command), *args)
                    def write(result):
                        response = xmlrpclib.dumps((result,),
                                                   methodresponse=True)
                        request.write(response)
                        request.finish()
                    def error(reason):
                        log.error("Unable to fetch graph: %s", reason)
                        request.finish()
                    d.addCallbacks(write, error)
                    return server.NOT_DONE_YET
                except Exception, ex:
                    log.exception(ex)
                    log.warning("Skipping renderer %s" % instance)
        raise Exception("No renderer registered")

    def getChild(self, path, request):
        "Handle all paths"
        return self, ()


    def addRenderer(self, renderer):
        self.renderers[renderer.instance] = renderer

class ZenRender(HubService):

    def __init__(self, *args, **kw):
        HubService.__init__(self, *args, **kw)
        global htmlResource
        if not htmlResource:
            htmlResource = Render()
            reactor.listenTCP(8090, server.Site(htmlResource))
        htmlResource.addRenderer(self)
    
