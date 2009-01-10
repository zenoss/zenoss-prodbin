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

__doc__='''MultiGraphReportClass

MultiGraphReportClass contain MultiGraphReports.
'''

from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from ReportClass import ReportClass
from Products.ZenRelations.RelSchema import *
from Globals import InitializeClass
from Products.ZenWidgets import messaging


def manage_addMultiGraphReportClass(context, id, title = None, REQUEST = None):
    ''' Construct a new MultiGraphreportclass
    '''
    frc = MultiGraphReportClass(id, title)
    context._setObject(id, frc)
    if REQUEST is not None:
        messaging.IMessageSender(self).sendToBrowser(
            'Organizer Created',
            'Report organizer %s was created.' % id
        )
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addMultiGraphReportClass = DTMLFile('dtml/addMultiGraphReportClass',globals())

class MultiGraphReportClass(ReportClass):

    portal_type = meta_type = "MultiGraphReportClass"

    # Remove this relationship after version 2.1
    _relations = ReportClass._relations +  (
        ('graphDefs', 
            ToManyCont(ToOne, 'Products.ZenModel.GraphDefinition', 'reportClass')),
        )
    
    security = ClassSecurityInfo()
    
    def getReportClass(self):
        ''' Return the class to instantiate for new report classes
        '''
        return MultiGraphReportClass


    security.declareProtected('Manage DMD', 'manage_addMultiGraphReport')
    def manage_addMultiGraphReport(self, id, REQUEST=None):
        """Add an MultiGraph report to this object.
        """
        from Products.ZenModel.MultiGraphReport import MultiGraphReport
        fr = MultiGraphReport(id)
        self._setObject(id, fr)
        if REQUEST:
            url = '%s/%s/editMultiGraphReport' % (self.getPrimaryUrlPath(), id)
            return REQUEST['RESPONSE'].redirect(url)
        return self._getOb(id)


InitializeClass(MultiGraphReportClass)
