###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, 2011 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """RenderConfig
zenhub service to start looking for requests to render performance graphs
"""

import logging
log = logging.getLogger('zen.HubService.RenderConfig')

import Globals
from Products.ZenCollector.services.config import NullConfigService

from twisted.web import resource, server
from twisted.internet import reactor
from twisted.internet.error import CannotListenError
import xmlrpclib, mimetypes

# Global variable
htmlResource = None


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

        listener = request.postpath[-2]
        command = request.postpath[-1]
        args.setdefault('ftype', 'PNG')
        ftype = args['ftype']
        del args['ftype']
        mimetype = mimetypes.guess_type('x.%s' % ftype)[0]
        if mimetype is None:
            mimetype = 'image/%s' % ftype.lower()
        request.setHeader('Content-type', mimetype)
        def write(result):
            if result:
                request.write(result)
            request.finish()
        def error(reason):
            log.error("Unable to fetch graph: %s", reason)
            request.finish()
        renderer = self.renderers.get(listener, False)
        if not renderer or not renderer.listeners:
            raise Exception("Renderer %s unavailable" % listener)
        d = renderer.listeners[0].callRemote(command, **args)
        d.addCallbacks(write, error)
        return server.NOT_DONE_YET

    def render_POST(self, request):
        "Deal with XML-RPC requests"
        content = request.content.read()
        for instance, renderer in self.renderers.items():
            if instance != request.postpath[-1]: continue
            for listener in renderer.listeners:
                try:
                    args, command = xmlrpclib.loads(content)
                    request.setHeader('Content-type', 'text/xml')
                    d = listener.callRemote(str(command), *args)
                    def write(result):
                        try:
                            response = xmlrpclib.dumps((result,),
                                                       methodresponse=True,
                                                       allow_none=True)
                            request.write(response)
                        except Exception, ex:
                            log.error("Unable to %s: %s", command, ex)
                        request.finish()
                    def error(reason):
                        log.error("Unable to %s: %s", command, reason)
                        request.finish()
                    d.addCallbacks(write, error)
                    return server.NOT_DONE_YET
                except Exception, ex:
                    log.exception(ex)
                    log.warning("Skipping renderer %s" % instance)
        raise Exception("No renderer registered")

    def getChild(self, unused, ignored):
        "Handle all paths"
        return self, ()

    def addRenderer(self, renderer):
        self.renderers[renderer.instance] = renderer


class RenderConfig(NullConfigService):
    def __init__(self, dmd, instance):
        NullConfigService.__init__(self, dmd, instance)
        global htmlResource
        try:
            if not htmlResource:
                htmlResource = Render()
                log.info("Starting graph retrieval listener on port 8090")
                reactor.listenTCP(8090, server.Site(htmlResource))
            htmlResource.addRenderer(self)
        except CannotListenError, e:
            # Probably in a hub worker; no big deal
            log.debug("Not starting render listener because the port is "
                      "already in use.")

