##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


"""RenderConfig

zenhub service to start looking for requests to render performance graphs.
"""

from Products.ZenUtils.Utils import ipv6_available

import logging
log = logging.getLogger('zen.HubService.RenderConfig')

import Globals
from Products.ZenCollector.services.config import NullConfigService
from Products.ZenRRD.zenrender import RenderServer

from twisted.web import resource, server
from twisted.internet import reactor
from twisted.internet.error import CannotListenError
import socket
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

        command = request.postpath[-1]
        if command in ('favicon.ico',):
            log.debug("Received a bad request: %s", command)
            return ''
        from Products.ZenHub import ZENHUB_ZENRENDER
        if len(request.postpath) > 1:
            listener = request.postpath[-2]
        else:
            listener = ZENHUB_ZENRENDER
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
        if renderer and listener == ZENHUB_ZENRENDER:
            try:
                rs = RenderServer(listener)
                renderFn = getattr(rs,command)
                result = renderFn(**args)
                reactor.callLater(0,write, result)
            except Exception as e:
                log.exception("Exception getting graph")
                reactor.callLater(0,error, e.msg)
        else:
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
        from Products.ZenHub import ZENHUB_ZENRENDER
        if instance == ZENHUB_ZENRENDER:
            self.dmd = dmd
            self.instance = instance
        else:
            NullConfigService.__init__(self, dmd, instance)

        global htmlResource
        try:
            if not htmlResource:
                htmlResource = Render()
                log.info("Starting graph retrieval listener on port 8090")
                interface = '::' if ipv6_available() else ''
                reactor.listenTCP(8090, server.Site(htmlResource), interface=interface)
            htmlResource.addRenderer(self)
        except CannotListenError, e:
            # Probably in a hub worker; no big deal
            log.debug("Not starting render listener because the port is "
                      "already in use.")
