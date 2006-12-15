#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################
__doc__="""ReportServer

A front end to all the report plugins.

$Id: $"""

__version__ = "$Revision: $"[11:-2]

from Globals import InitializeClass

from AccessControl import ClassSecurityInfo

from Products.ZenModel.ZenModelRM import ZenModelRM
import os

class ReportServer(ZenModelRM):
    security = ClassSecurityInfo()
    security.setDefaultAccess('allow')

    security.declareProtected('View', 'plugin')
    def plugin(self, name, REQUEST):
        "Run a plugin to generate the report object"
        print 'running plugin'
        dmd = self.dmd
        args = dict(zip(REQUEST.keys(), REQUEST.values()))
        report = None
        m = os.path.join(os.environ['ZENHOME'],
                         'Products/ZenReports/plugins/%s.py' % name)
        exec open(m)
        return report

def manage_addReportServer(context, id, REQUEST = None):
    """make a ReportServer"""
    rs = ReportServer(id)
    context._setObject(id, rs)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')

        
InitializeClass(ReportServer)
