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

__doc__="""CustomDeviceReportClass

CustomDeviceReportClass contain CustomDeviceReports.
"""

from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from ReportClass import ReportClass
from Globals import InitializeClass
from Products.ZenWidgets import messaging
from Products.ZenUtils.deprecated import deprecated
from Products.ZenMessaging.audit import audit
from Products.ZenUtils.Utils import getDisplayType
from Products.ZenModel.DeviceReport import DeviceReport

@deprecated
def manage_addCustomDeviceReportClass(context, id, title = None, REQUEST = None):
    """ Construct a new CustomDeviceReportclass
    """
    frc = CustomDeviceReportClass(id, title)
    context._setObject(id, frc)
    if REQUEST is not None:
        audit('UI.ReportClass.Add', frc.id, title=title, organizer=context)
        messaging.IMessageSender(context).sendToBrowser(
            'Report Organizer Added',
            'Custom report organizer %s has been created.' % id
        )
        return REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addCustomDeviceReportClass = DTMLFile('dtml/addCustomDeviceReportClass',globals())

class CustomDeviceReportClass(ReportClass):

    portal_type = meta_type = "CustomDeviceReportClass"
    
    security = ClassSecurityInfo()

    def getReportClass(self):
        """ Return the class to instantiate for new report classes
        """
        return CustomDeviceReportClass


    security.declareProtected('Manage DMD', 'manage_addDeviceReport')
    def manage_addDeviceReport(self, id, REQUEST=None):
        """Add a custom device report to this object.
        """
        rpt = DeviceReport(id)
        self._setObject(rpt.id, rpt)
        rpt = self._getOb(rpt.id)
        if REQUEST:
            audit('UI.Report.Add', rpt.id, reportType=getDisplayType(rpt))
            url = '%s/%s/editDeviceReport' % (self.getPrimaryUrlPath(), id)
            return REQUEST['RESPONSE'].redirect(url)
        return rpt


InitializeClass(CustomDeviceReportClass)
