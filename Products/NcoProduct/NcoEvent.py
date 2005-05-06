#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

"""NcoEvent

Object to represent an NcoEvent.  Its main function is to display
itself as an HTML row in event list

$Id: NcoEvent.py,v 1.12 2004/04/22 19:08:47 edahl Exp $"""

__version__ = "$Revision: 1.12 $"[11:-2]

from Acquisition import Implicit
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from Products.CMFCore import permissions

from Products.ZenModel.ConfmonAll import ConfmonAll

class NcoEvent(Implicit):
    security = ClassSecurityInfo()
    security.setDefaultAccess("allow")
    def __init__(self, data, fields):
        #when NcoProduct makes an event it adds
        #four fields on to the end of the field list
        from NcoManager import defaultFields
        defaultLen = len(defaultFields)
        self.data = data[:-defaultLen]
        self.defaultdata = data[-defaultLen:]
        for i in range(len(fields)):
            setattr(self, fields[i], data[i])
        for i in range(len(defaultFields)):
            setattr(self, defaultFields[i], self.defaultdata[i])
        self.bgcolor = "#FFFFFF"
        self.fgcolor = "#000000"
        
  
    def getEventDetailHref(self):
        """build an href to call the detail of this event"""
        params = "/viewNcoEventFields?serverserial=%d&servername=%s" % (
                        self.ServerSerial, self.ServerName)
        return self.absolute_url() + params


    def getHistoryEventDetailHref(self):
        """build an href to call the detail of a history event"""
        return self.getEventDetailHref() + "&ev_ishist=1"


    def getfieldcount(self):
        """return the number of fields"""
        return len(self.data)

    def getfield(self, index):
        """return the value of a field"""
        return self.data[index]

    def getAllEventText(self):
        """return all the text of the event"""
        return " ".join(map(str,self.data))

    def getSeverityNumber(self):
        """return the severity as an integer"""
        return self.defaultdata[1]

InitializeClass(NcoEvent)

class NcoEventDetail(NcoEvent, ConfmonAll):
    security = ClassSecurityInfo()
    security.setDefaultAccess("allow")

    factory_type_information = ( 
        { 
            'id'             : 'NcoEventDetail',
            'meta_type'      : 'NcoEventDetail',
            'description'    : """Detail view of netcool event""",
            'icon'           : 'NcoEventDetail_icon.gif',
            'product'        : 'NcoProduct',
            'factory'        : '',
            'immediate_view' : 'viewNcoEventFields',
            'actions'        :
            ( 
                { 'id'            : 'fields'
                , 'name'          : 'Fields'
                , 'action'        : 'viewNcoEventFields'
                , 'permissions'   : (
                  permissions.View, )
                },
                { 'id'            : 'details'
                , 'name'          : 'Details'
                , 'action'        : 'viewNcoEventDetails'
                , 'permissions'   : (
                  permissions.View, )
                },
                { 'id'            : 'journal'
                , 'name'          : 'Journal'
                , 'action'        : 'viewNcoEventJournals'
                , 'permissions'   : (
                  permissions.View, )
                },
            )
          },
        )

    def __init__(self, data, fields, details=None, journals=None):
        NcoEvent.__init__(self, data, fields)
        self.fields = []
        for i in range(len(fields)):
            tdict = NcoEventData(fields[i], data[i])
            self.fields.append(tdict)
        self.details = details
        self.jounals = journals

    def getEventFields(self):
        """return an array of event fields dictionaries keys:(field,value)"""
        return self.fields

    def getEventDetails(self):
        """return array of details dictionaries keys:(field,value)"""
        return self.details

    def getEventJournals(self):
        """return an array of journal dictionaries keys:(user,date,text)"""
        return self.journals
        
InitializeClass(NcoEventDetail)

class NcoEventData:
    security = ClassSecurityInfo()
    security.setDefaultAccess("allow")
    def __init__(self, field, value):
        self.field = field
        self.value = value
InitializeClass(NcoEventData)


class NcoEventJournal:
    security = ClassSecurityInfo()
    security.setDefaultAccess("allow")
    def __init__(self, user, date, text):
        self.user = user
        self.date = date
        self.text = text

InitializeClass(NcoEventJournal)
