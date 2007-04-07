import Globals

from Products.ZenHub.PBDaemon import PBDaemon
from Products.ZenModel.PerformanceConf import performancePath
from RenderServer import RenderServer as OrigRenderServer
from Products.ZenUtils.ObjectCache import ObjectCache

import os

class RenderServer(OrigRenderServer):

    cache = None

    def setupCache(self):
        """make new cache if we need one"""
        if self.cache is None:
            self.cache = ObjectCache()
            self.cache.initCache()
        return self.cache
    

class zenrender(PBDaemon):

    initialServices = ['ZenRender']

    def __init__(self):
        PBDaemon.__init__(self, 'zenrender')
        self.rs = RenderServer(self.name)

    def remote_render(self, gopts, drange, ftype):
        return self.rs.render(gopts, drange, ftype=ftype)

if __name__ == '__main__':
    zr = zenrender()
    zr.run()
