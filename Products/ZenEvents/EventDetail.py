
from Event import Event
from Products.ZenModel.ZenModelItem import ZenModelItem
from Acquisition import Implicit

from AccessControl import Permissions as permissions
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

class EventDetail(Event, ZenModelItem, Implicit):
    security = ClassSecurityInfo()
    security.setDefaultAccess("allow")

    factory_type_information = ( 
        { 
            'id'             : 'EventDetail',
            'meta_type'      : 'EventDetail',
            'description'    : """Detail view of netcool event""",
            'icon'           : 'EventDetail_icon.gif',
            'product'        : 'NcoProduct',
            'factory'        : '',
            'immediate_view' : 'viewNcoEventFields',
            'actions'        :
            ( 
                { 'id'            : 'fields'
                , 'name'          : 'Fields'
                , 'action'        : 'viewNcoEventFields'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'details'
                , 'name'          : 'Details'
                , 'action'        : 'viewNcoEventDetails'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'journal'
                , 'name'          : 'Journal'
                , 'action'        : 'viewNcoEventJournals'
                , 'permissions'   : (
                  permissions.view, )
                },
            )
          },
        )

    def __init__(self, manager, data, fields, details=None, journals=None):
        Event.__init__(self, manager, data, fields)
        self.fields = []
        for i in range(len(fields)):
            tdict = EventData(fields[i], data[i])
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
        
InitializeClass(EventDetail)

class EventData:
    security = ClassSecurityInfo()
    security.setDefaultAccess("allow")
    def __init__(self, field, value):
        self.field = field
        self.value = value
InitializeClass(EventData)


class EventJournal:
    security = ClassSecurityInfo()
    security.setDefaultAccess("allow")
    def __init__(self, user, date, text):
        self.user = user
        self.date = date
        self.text = text

InitializeClass(EventJournal)
