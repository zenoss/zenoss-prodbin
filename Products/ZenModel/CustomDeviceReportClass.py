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

__doc__='''CustomDeviceReportClass

CustomDeviceReportClass contain CustomDeviceReports.
'''

from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from ReportClass import ReportClass
from ZenossSecurity import ZEN_MANAGE_DMD
from Globals import InitializeClass


def manage_addCustomDeviceReportClass(context, id, title = None, REQUEST = None):
    ''' Construct a new CustomDeviceReportclass
    '''
    frc = CustomDeviceReportClass(id, title)
    context._setObject(id, frc)
    if REQUEST is not None:
        REQUEST['message'] = "Report organizer created"
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addCustomDeviceReportClass = DTMLFile('dtml/addCustomDeviceReportClass',globals())

class CustomDeviceReportClass(ReportClass):

    portal_type = meta_type = "CustomDeviceReportClass"
    
    security = ClassSecurityInfo()

    def getReportClass(self):
        ''' Return the class to instantiate for new report classes
        '''
        return CustomDeviceReportClass


    security.declareProtected('Manage DMD', 'manage_addDeviceReport')
    def manage_addDeviceReport(self, id, REQUEST=None):
        """Add a report to this object.
        """
        from Products.ZenModel.DeviceReport import DeviceReport
        rpt = DeviceReport(id)
        self._setObject(rpt.id, rpt)
        if REQUEST:
            url = '%s/%s/editDeviceReport' % (self.getPrimaryUrlPath(), id)
            REQUEST['RESPONSE'].redirect(url)
        return rpt


InitializeClass(CustomDeviceReportClass)
