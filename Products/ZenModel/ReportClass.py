#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""ReportClass

ReportClass groups different types of reports together

$Id: ReportClass.py,v 1.3 2004/04/22 15:33:44 edahl Exp $"""

__version__ = "$Revision: 1.3 $"[11:-2]

import types

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from OFS.Folder import Folder
from Globals import DTMLFile

from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from Organizer import Organizer
from Report import Report

def manage_addReportClass(context, id, title = None, REQUEST = None):
    """make a device class"""
    dc = ReportClass(id, title)
    context._setObject(id, dc)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addReportClass = DTMLFile('dtml/addReportClass',globals())

class ReportClass(Organizer):
    dmdRootName = "Reports"
    portal_type = meta_type = "ReportClass"

    sub_meta_types = ("ReportClass", "Report", 'DeviceReport')

    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'immediate_view' : 'viewReportClass',
            'actions'        :
            ( 
                { 'id'            : 'view'
                , 'name'          : 'View'
                , 'action'        : 'viewReportClass'
                , 'permissions'   : ( "View",)
                , 'visible'       : 0
                },
            )
          },
        )
    
    security = ClassSecurityInfo()


    def reports(self):
        """Return list of report instances.
        """
        return [ r for r in self.objectValues(spec=('Report','DeviceReport')) ]

        
    def countReports(self):
        """Return a count of all our contained children."""
        count = len(self.reports())
        for child in self.children():
            count += child.countReports()
        return count
        

    security.declareProtected('Manage DMD', 'manage_addDeviceReport')
    def manage_addDeviceReport(self, id, REQUEST=None):
        """Add an action rule to this object.
        """
        from Products.ZenModel.DeviceReport import DeviceReport
        dr = DeviceReport(id)
        self._setObject(id, dr)
        if REQUEST:
            return self.callZenScreen(REQUEST)

    
    def moveReports(self, moveTarget, ids=None, REQUEST=None):
        """Move a report from here organizer to moveTarget.
        """
        if not moveTarget or not ids: return self()
        if type(ids) in types.StringTypes: ids = (ids,)
        target = self.getOrganizer(moveTarget)
        for rptname in ids:
            rpt = self._getOb(rptname)
            rpt._operation = 1 # moving object state
            self._delObject(rptname)
            target._setObject(rptname, rpt)
        if REQUEST:
            REQUEST['RESPONSE'].redirect(target.getPrimaryUrlPath())
    
     
InitializeClass(ReportClass)
