import os
import time
import logging

import urllib

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from Globals import DTMLFile
from OFS.Image import manage_addFile

try:
    import rrdtool
except ImportError:
    pass

from Products.ZenUtils.PObjectCache import PObjectCache
from Products.ZenUtils.PObjectCache import CacheObj

from RenderServer import RenderServer

import utils

log = logging.getLogger("ProxyRenderServer")

from RenderServer import RenderServer,addRenderServer,manage_addRenderServer

def manage_addProxyRenderServer(context, id, REQUEST = None):
    """make a ProxyRenderServer"""
    rs = ProxyRenderServer(id)
    context._setObject(id, rs)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
                                     

addProxyRenderServer = DTMLFile('dtml/addProxyRenderServer',globals())

class ProxyRenderServer(RenderServer):

    meta_type = "ProxyRenderServer"

    cacheName = 'RRDRenderCache'
    
    security = ClassSecurityInfo()

    def __init__(self, id, tmpdir = '/tmp/renderserver', cachetimeout=300):
        self.id = id
        self.tmpdir = tmpdir
        self.cachetimeout = cachetimeout

    security.declareProtected('View', 'render')
    def render(self, gopts, drange, ftype='PNG', REQUEST=None):
        """render a graph and return it"""
        gopts = gopts.split('|')
        gopts = [g for g in gopts if g]
        drange = int(drange)
        id = self.graphId(gopts, drange, ftype)
        graph = self.getGraph(id, ftype, REQUEST)
        if not graph:
            if not os.path.exists(self.tmpdir):
                os.makedirs(self.tmpdir)
            filename = "%s/graph-%s" % (self.tmpdir,id)

            renderurl = self.Monitors.Performance.localhost.renderurl
            url = "%s/render?gopts=%s&drange=%d" % (renderurl,gopts,drange)
            f = open(filename, "wb")
            f.write(urllib.urlopen(url).read())
            f.close()
            
            return self._loadfile(filename)
            self.addGraph(id, filename)
            graph = self.getGraph(id, ftype, REQUEST)
        return graph 

InitializeClass(ProxyRenderServer)
