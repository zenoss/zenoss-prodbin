
from Products.ZenHub.HubService import HubService
from twisted.web import resource, server
from twisted.internet import reactor

htmlResource = None

import logging
log = logging.getLogger("zenrender")

class Render(resource.Resource):

    isLeaf = True

    def __init__(self):
        resource.Resource.__init__(self)
        self.renderers = {}

    def render_GET(self, request):
        gopts = request.args['gopts'][0]
        drange = request.args['drange'][0]
        ftype = request.args.get('ftype', ['PNG'])[0]
        for instance, renderer in self.renderers.items():
            for listener in renderer.listeners:
                try:
                    d = listener.callRemote('render', gopts, drange, ftype)
                    request.setHeader('Content-type', 'image/%s' % ftype)
                    def write(result):
                        request.write(result)
                        request.finish()
                    def error(reason):
                        log.error("Unable to fetch graph: %s", reason)
                        request.finish()
                    d.addCallbacks(write, error)
                    return server.NOT_DONE_YET
                except Exception, ex:
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
    
