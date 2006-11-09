#################################################################
#
#   Copyright (c) 2003 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""RenderServer

Frontend that passes rrd graph options to rrdtool to render.  

$Id: RenderServer.py,v 1.14 2003/06/04 18:25:58 edahl Exp $"""

__version__ = "$Revision: 1.14 $"[11:-2]

import os
import time
import logging

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

from RRDToolItem import RRDToolItem

import utils

log = logging.getLogger("RenderServer")


def manage_addRenderServer(context, id, REQUEST = None):
    """make a RenderServer"""
    rs = RenderServer(id)
    context._setObject(id, rs)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
                                     

addRenderServer = DTMLFile('dtml/addRenderServer',globals())


class RenderServer(RRDToolItem):

    meta_type = "RenderServer"

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
            gopts.insert(0, "--imgformat=%s" % ftype)
            #gopts.insert(0, "--lazy")
            end = int(time.time())-300
            start = end - drange
            gopts.insert(0, '--end=%d' % end)
            gopts.insert(0, '--start=%d' % start)
            if not os.path.exists(self.tmpdir):
                os.makedirs(self.tmpdir)
            filename = "%s/graph-%s" % (self.tmpdir,id)
            gopts.insert(0, filename)
            log.debug(" ".join(gopts))
            try:
                rrdtool.graph(*gopts)
            except:    
                log.exception("failed generating graph")
                log.warn(" ".join(gopts))
                raise
            return self._loadfile(filename)
            self.addGraph(id, filename)
            graph = self.getGraph(id, ftype, REQUEST)
        return graph 


    security.declareProtected('View', 'plugin')
    def plugin(self, name, REQUEST=None):
        "render a custom graph and return it"
        try:
            m = os.path.join(os.environ['ZENHOME'],
                             'Products/ZenRRD/plugins/%s.py' % name)
            exec open(m)
            return graph
        except Exception, ex:
            log.exception("failed generating graph from plugin %s" % name)
            raise


    security.declareProtected('GenSummary', 'summary')
    def summary(self, gopts, drange):
        """return summary information as a list but no graph"""
        drange = int(drange)
        end = int(time.time())-300
        start = end - drange
        gopts.insert(0, '--end=%d' % end)
        gopts.insert(0, '--start=%d' % start)
        gopts.insert(0, '/dev/null') #no graph generated
        try:
            values = rrdtool.graph(*gopts)[2]
        except:
            log.exception("failed generating summary")
            log.warn(" ".join(gopts))
            raise
        return values
        

    security.declareProtected('GenSummary', 'currentValues')
    def currentValues(self, paths):
        """return latest values"""
        gopts = ['/dev/null']
        for i, p in enumerate(paths):
            gopts.append("DEF:x%d_r=%s:ds0:AVERAGE" % (i,p))
            gopts.append("VDEF:v%d=x%d_r,LAST" % (i, i))
            gopts.append("PRINT:v%d:%%.2lf" % (i))
        gopts.append('--end=now')
        gopts.append('--start=now-300')
        try:
            values = rrdtool.graph(*gopts)[2]
            if values:
                if values.count('nan') > 0:
                    raise ValueError('Data Unavailable')
                values = map(float, values)
            else:
                values = []
        except NameError:
            log.warn("It appears that the rrdtool bindings are not installed properly.")
            values = []
        except:
            log.exception("failed generating summary")
            log.warn(" ".join(gopts))
            raise
        return values
        

    def rrdcmd(self, gopts, ftype='PNG'):
        filename, gopts = self._setfile(gopts, ftype)
        return "rrdtool graph " + " ".join(gopts)


    def graphId(self, gopts, drange, ftype):
        import md5
        id = md5.new(''.join(gopts)).hexdigest() 
        id += str(drange) + '.' + ftype.lower()
        return id
    
    def _loadfile(self, filename):
        f = open(filename)
        graph = f.read()
        f.close()
        return graph


    def setupCache(self):
        """make new cache if we need one"""
        if not hasattr(self, '_v_cache') or not self._v_cache:
            tmpfolder = self.getPhysicalRoot().temp_folder
            if not hasattr(tmpfolder, self.cacheName):
                cache = PObjectCache(self.cacheName, self.cachetimeout)
                tmpfolder._setObject(self.cacheName, cache)
            self._v_cache = tmpfolder._getOb(self.cacheName)
        return self._v_cache


    def addGraph(self, id, filename):
        """add graph to temporary folder"""
        cache = self.setupCache()
        graph = self._loadfile(filename)
        cache.addToCache(id, graph)


    def getGraph(self, id, ftype, REQUEST):
        """get a previously generated graph"""
        cache = self.setupCache()
        ftype = ftype.lower()
        if REQUEST:
            response = REQUEST.RESPONSE
            response.setHeader('Content-Type', 'image/%s'%ftype)
        return cache.checkCache(id)


InitializeClass(RenderServer)
