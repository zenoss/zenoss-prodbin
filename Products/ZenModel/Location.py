#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""Location

Location is a base class that represents a physical
location where a collection of devices resides.

$Id: Location.py,v 1.12 2004/04/22 19:08:47 edahl Exp $"""

__version__ = "$Revision: 1.12 $"[11:-2]

from Globals import InitializeClass
from Globals import DTMLFile

from AccessControl import ClassSecurityInfo

from Products.CMFCore import CMFCorePermissions

from DeviceGroupInt import DeviceGroupInt

from LocationBase import LocationBase

def manage_addLocation(context, id, description = "", REQUEST = None):
    """make a Location"""
    loc = Location(id)
    context._setObject(id, loc)
    loc.description = description
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addLocation = DTMLFile('dtml/addLocation',globals())

class Location(LocationBase):
    """Location object"""
    portal_type = meta_type = 'Location'
    
    _properties = (
                    {'id':'description', 'type':'string', 'mode':'w'},
                   ) 

    description = ""

    factory_type_information = ( 
        { 
            'id'             : 'Location',
            'meta_type'      : 'Location',
            'description'    : """Class representing arbitrary locations""",
            'icon'           : 'Location_icon.gif',
            'product'        : 'Confmon',
            'factory'        : 'manage_addLocation',
            'immediate_view' : 'viewLocationOverview',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewLocationOverview'
                , 'permissions'   : (
                  CMFCorePermissions.View, )
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'locationEvents'
                , 'permissions'   : (
                  CMFCorePermissions.View, )
                },
                { 'id'            : 'historyEvents'
                , 'name'          : 'History'
                , 'action'        : 'locationHistoryEvents'
                , 'permissions'   : (
                  CMFCorePermissions.View, )
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (
                  CMFCorePermissions.View, )
                },
                { 'id'            : 'view'
                , 'name'          : 'View'
                , 'action'        : 'viewItem'
                , 'permissions'   : (
                  CMFCorePermissions.View, )
                , 'visible'       : 0
                },
            )
          },
        )

    security = ClassSecurityInfo()

    #need to decuple these two methods out to actions
    security.declareProtected('View', 'locationEvents')
    def locationEvents(self):
        """get the event list of this object"""
        self.REQUEST.set('ev_whereclause', "Location like '%s.*'" %
                                    self.getLocationName())
        return self.viewEvents(self.REQUEST)


    security.declareProtected('View', 'locationHistoryEvents')
    def locationHistoryEvents(self):
        """get the history event list of this object"""
        self.REQUEST.set('ev_whereclause', "Location like '%s%%'" %
                                    self.getLocationName())
        self.REQUEST.set('ev_orderby', "LastOccurrence desc")
        return self.viewHistoryEvents(self.REQUEST)



    security.declareProtected('View', 'countDevices')
    def countDevices(self):
        """count all devices with in a location"""
        count = self.devices.countObjects()
        for rack in self.racks():
            count += rack.countDevices()
        for loc in self.sublocations():
            count += loc.countDevices()
        return count


    def getLocationNames(self):
        """build a list of the full paths of all sub locations and racks""" 
        locnames = LocationBase.getLocationNames(self)
        for rack in self.racks():
            locnames.append(rack.getLocationName())
        return locnames 

    
InitializeClass(LocationBase)
