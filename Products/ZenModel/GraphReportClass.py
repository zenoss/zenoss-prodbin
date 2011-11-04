###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__="""GraphReportClass

GraphReportClass contain GraphReports.
"""

from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from ReportClass import ReportClass
from Globals import InitializeClass
from Products.ZenWidgets import messaging
from Products.ZenMessaging.audit import audit
from Products.ZenUtils.Utils import getDisplayType
from Products.ZenUtils.deprecated import deprecated
from Products.ZenModel.GraphReport import GraphReport

@deprecated
def manage_addGraphReportClass(context, id, title = None, REQUEST = None):
    """ Construct a new GraphReportclass
    """
    rc = GraphReportClass(id, title)
    context._setObject(rc.id, rc)
    if REQUEST is not None:
        audit('UI.ReportClass.Add', rc.id, title=title, organizer=context)
        messaging.IMessageSender(context).sendToBrowser(
            'Report Organizer Created',
            'Report organizer %s was created.' % id
        )
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main')

addGraphReportClass = DTMLFile('dtml/addGraphReportClass',globals())

class GraphReportClass(ReportClass):

    portal_type = meta_type = "GraphReportClass"

    security = ClassSecurityInfo()

    def getReportClass(self):
        """ Return the class to instantiate for new report classes
        """
        return GraphReportClass


    security.declareProtected('Manage DMD', 'manage_addGraphReport')
    def manage_addGraphReport(self, id, REQUEST=None):
        """Add a graph report to this object.
        """
        fr = GraphReport(id)
        self._setObject(id, fr)
        fr = self._getOb(id)
        if REQUEST:
            audit('UI.Report.Add', fr.id, reportType=getDisplayType(fr))
            url = '%s/%s/editGraphReport' % (self.getPrimaryUrlPath(),id)
            return REQUEST['RESPONSE'].redirect(url)
        return fr


InitializeClass(GraphReportClass)
