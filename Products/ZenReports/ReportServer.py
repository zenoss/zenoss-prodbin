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
__doc__ = """ReportServer

A front end to all the report plugins.

"""


import os
import sys
import logging
log = logging.getLogger('zen.reportserver')

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenUtils.Utils import importClass, zenPath
from Products.ZenModel.ZenossSecurity import *


class ReportServer(ZenModelRM):
    security = ClassSecurityInfo()
    security.setDefaultAccess('allow')

    security.declareProtected(ZEN_COMMON, 'plugin')
    def plugin(self, name, REQUEST, templateArgs = None):
        "Run a plugin to generate the report object"
        dmd = self.dmd
        args = dict(zip(REQUEST.keys(), REQUEST.values()))

        # We don't want the response object getting passed to the plugin
        # because if it is stringified, it can modify the return code
        # and cause problems upstream.
        if 'RESPONSE' in args:
            del args['RESPONSE']

        directories = []
        for p in self.ZenPackManager.packs():
            try:
                pluginpath = p.path('reports', 'plugins')
                directories.append(pluginpath)
            except AttributeError:
                log.error("Unable to load report plugin %s for ZenPack %s",
                          name, p.id)
        directories.append(zenPath('Products/ZenReports/plugins'))
        
        klass = None
        for d in directories:
            if os.path.exists('%s/%s.py' % (d, name)):
                try:
                    sys.path.insert(0, d)
                    klass = importClass(name)
                    break
                finally:
                    sys.path.remove(d)
        if not klass:
            raise IOError('Unable to find plugin named "%s"' % name)
        instance = klass()
        if templateArgs == None:
            return instance.run(dmd, args)
        else:
            return instance.run(dmd, args, templateArgs)

def manage_addReportServer(context, id, REQUEST = None):
    """make a ReportServer"""
    rs = ReportServer(id)
    context._setObject(id, rs)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')

        
InitializeClass(ReportServer)
