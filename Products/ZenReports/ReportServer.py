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
__doc__="""ReportServer

A front end to all the report plugins.

$Id: $"""

__version__ = "$Revision: $"[11:-2]

from Globals import InitializeClass

from AccessControl import ClassSecurityInfo

from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenUtils.Utils import importClass

import os
import sys

class ReportServer(ZenModelRM):
    security = ClassSecurityInfo()
    security.setDefaultAccess('allow')

    security.declareProtected('View', 'plugin')
    def plugin(self, name, REQUEST):
        "Run a plugin to generate the report object"
        dmd = self.dmd
        args = dict(zip(REQUEST.keys(), REQUEST.values()))
        m = os.path.join(os.environ['ZENHOME'],
                         'Products/ZenReports/plugins')
        directories = [
            p.path('reports', 'plugins') for p in self.packs()
            ] + [m]
        
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
        return instance.run(dmd, args)

def manage_addReportServer(context, id, REQUEST = None):
    """make a ReportServer"""
    rs = ReportServer(id)
    context._setObject(id, rs)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')

        
InitializeClass(ReportServer)
