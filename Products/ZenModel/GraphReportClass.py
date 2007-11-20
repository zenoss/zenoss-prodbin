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

__doc__='''GraphReportClass

GraphReportClass contain GraphReports.
'''

from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from ReportClass import ReportClass
from Globals import InitializeClass


def manage_addGraphReportClass(context, id, title = None, REQUEST = None):
    ''' Construct a new GraphReportclass
    '''
    rc = GraphReportClass(id, title)
    context._setObject(rc.id, rc)
    if REQUEST is not None:
        REQUEST['message'] = "Report organizer created"
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addGraphReportClass = DTMLFile('dtml/addGraphReportClass',globals())

class GraphReportClass(ReportClass):

    portal_type = meta_type = "GraphReportClass"
    
    security = ClassSecurityInfo()

    def getReportClass(self):
        ''' Return the class to instantiate for new report classes
        '''
        return GraphReportClass


    security.declareProtected('Manage DMD', 'manage_addGraphReport')
    def manage_addGraphReport(self, id, REQUEST=None):
        """Add an MultiGraph report to this object.
        """
        from Products.ZenModel.GraphReport import GraphReport
        fr = GraphReport(id)
        self._setObject(id, fr)
        fr = self._getOb(id)
        if REQUEST:
            url = '%s/%s/editGraphReport' % (self.getPrimaryUrlPath(),id)
            return REQUEST['RESPONSE'].redirect(url)
        return fr


InitializeClass(GraphReportClass)
