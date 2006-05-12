#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

import cgi
import types

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from Products.ZenUtils.ZenTales import talesEval

#from Report import Report
from ZenModelRM import ZenModelRM

class DeviceReport(ZenModelRM):

    meta_type = "DeviceReport"

    path = "/"
    deviceQuery = ""
    sortedHeader = ""
    sortedSence = "asc"
    groupby = ""
    columns = []
    colnames = []

    _properties = ZenModelRM._properties + (
        {'id':'path', 'type':'string', 'mode':'w'},
        {'id':'deviceQuery', 'type':'string', 'mode':'w'},
        {'id':'sortedHeader', 'type':'string', 'mode':'w'},
        {'id':'sortedSence', 'type':'string', 'mode':'w'},
        {'id':'groupby', 'type':'string', 'mode':'w'},
        {'id':'columns', 'type':'lines', 'mode':'w'},
        {'id':'colnames', 'type':'lines', 'mode':'w'},
    )


    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'immediate_view' : 'viewDeviceReport',
            'actions'        :
            ( 
                {'name'          : 'Report',
                'action'        : 'viewDeviceReport',
                'permissions'   : ("View",),
                },
                {'name'          : 'Edit',
                'action'        : 'editDeviceReport',
                'permissions'   : ("Manage DMD",),
                },
            )
         },
        )

    security = ClassSecurityInfo()


    def getDevices(self):
        """Return the device list for this report.
        """
        devs = self.getDmdRoot("Devices")
        if self.path != "/": devs = devs.getOrganizer(self.path)
        devlist = devs.getSubDevices()
        if self.deviceQuery:
            return [ dev for dev in devlist \
                        if talesEval("python:"+self.deviceQuery, dev) ]
        return devlist
            

    def testQueryStyle(self):
        """Return red text style if query is bad.
        """
        try:
            self.getDevices()
        except:
            return "color:#FF0000"
   

    def testColNamesStyle(self):
        """Return red text style if columns and colnames not the same length.
        """
        if len(self.columns) != len(self.colnames): return "color:#FF0000"


    def reportHeader(self):
        h = []
        tname = self.getPrimaryId()
        for i, field in enumerate(self.columns):
            try:name = self.colnames[i]
            except IndexError: name = field
            h.append(self.ZenTableManager.getTableHeader(tname , field, name))
        return "\n".join(h)

            
    def reportBody(self): 
        """body of this report create from a filtered and sorted batch.
        """
        batch = self.ZenTableManager.getBatch(
                    self.getPrimaryId(), self.getDevices(), 
                    sortedHeader=self.sortedHeader, 
                    sortedSence=self.sortedSence)
        body = []
        for dev in batch:
            body.append("<tr class='tablevalues'>") 
            for field in self.columns:
                body.append("<td>")
                attr = getattr(dev, field)
                if callable(attr): value = attr()
                else: value = attr
                if type(value) in (types.ListType, types.TupleType):
                    value = ", ".join(value)
                if not field.endswith("Link"): value = cgi.escape(value)
                body.append(value)
                body.append("</td>")
            body.append("</tr>")
        return "\n".join(body)


InitializeClass(DeviceReport)
