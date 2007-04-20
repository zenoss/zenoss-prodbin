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
#! /usr/bin/env python 

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

    def remote_currentValues(self, *args, **kw):
        return self.rs.currentValues(*args, **kw)


if __name__ == '__main__':
    zr = zenrender()
    zr.run()
