
from Acquisition import Explicit
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from Products.ZenModel.ZenModelBase import ZenModelBase


class EventDetail(NcoEvent, ZenModelBase, Explicit):
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
        
InitializeClass(EventDetail)

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
