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

__doc__="""ReportClass

ReportClass groups different types of reports together

$Id: ReportClass.py,v 1.3 2004/04/22 15:33:44 edahl Exp $"""

__version__ = "$Revision: 1.3 $"[11:-2]

import types

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from Globals import DTMLFile

from Organizer import Organizer
from ZenPackable import ZenPackable
from ZenossSecurity import ZEN_COMMON
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.Utils import unused

def manage_addReportClass(context, id, title = None, REQUEST = None):
    """make a device class"""
    dc = ReportClass(id, title)
    context._setObject(id, dc)

    if REQUEST is not None:
        REQUEST['message'] = "Report organizer created"
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addReportClass = DTMLFile('dtml/addReportClass',globals())

class ReportClass(Organizer, ZenPackable):
    dmdRootName = "Reports"
    portal_type = meta_type = "ReportClass"

    #sub_meta_types = ("ReportClass", "Report", 'DeviceReport', 'GraphReport', 
    #                'MultiGraphReportClass')

    _relations = Organizer._relations + ZenPackable._relations
    
    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'immediate_view' : 'viewReportClass',
            'actions'        :
            ( 
                { 'id'            : 'view'
                , 'name'          : 'Status'
                , 'action'        : 'viewReportClass'
                , 'permissions'   : ( "View",)
                , 'visible'       : 1
                },
            )
          },
        )
    
    security = ClassSecurityInfo()

    security.declareProtected(ZEN_COMMON, "children")
    def children(self, sort=False, checkPerm=True, spec=None):
        ''' Return all objects that are instances of ReportClass
        '''
        unused(spec)
        kids = [o for o in self.objectValues() if isinstance(o, ReportClass)]
        if checkPerm:
            kids = [kid for kid in kids if self.checkRemotePerm("View", kid)]
        if sort: kids.sort(lambda x,y: cmp(x.primarySortKey(), 
                                           y.primarySortKey()))
        return kids


    def childIds(self, spec=None):
        """Return Ids of children within our organizer."""
        unused(spec)
        return [k.id for k in self.children()]


    security.declareProtected(ZEN_COMMON, "countChildren")
    def countChildren(self, spec=None):
        """Return a count of all our contained children."""
        unused(spec)
        count = len(self.childIds())
        for child in self.children():
            count += child.countChildren()
        return count


    def getReportClass(self):
        ''' Return the class to instantiate for new report classes
        '''
        return ReportClass


    def manage_addReportClass(self, id, title = None, REQUEST = None):
        """make a device class"""
        rClass = self.getReportClass()
        dc = rClass(id, title)
        self._setObject(id, dc)
        if REQUEST:
            REQUEST['message'] = "Report organizer created"
            return self.callZenScreen(REQUEST)


    def reports(self):
        """Return list of report instances.
        """
        reports = []
        for r in self.objectValues(
            spec=('Report','DeviceReport','GraphReport','MultiGraphReport')):
            if self.checkRemotePerm('View', r):
                reports.append(r)
        return reports
                

        
    def countReports(self):
        """Return a count of all our contained children."""
        count = len(self.reports())
        for child in self.children():
            count += child.countReports()
        return count
        

    security.declareProtected('Manage DMD', 'manage_addGraphReport')
    def manage_addGraphReport(self, id, REQUEST=None):
        """Add an graph report to this object.
        """
        if id:
            from Products.ZenModel.GraphReport import GraphReport
            gr = GraphReport(id)
            self._setObject(id, gr)
        if REQUEST:
            REQUEST['message'] = "Graph report created"
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
            REQUEST['message'] = "Device reports moved"
            REQUEST['RESPONSE'].redirect(target.getPrimaryUrlPath())
    

    def exportXmlHook(self, ofile, ignorerels):
        """patch to export all device components
        """
        from Acquisition import aq_base
        for o in self.reports():
            if hasattr(aq_base(o), 'exportXml'):
                o.exportXml(ofile, ignorerels)
     


InitializeClass(ReportClass)
