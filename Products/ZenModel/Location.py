#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""Location

$Id: Location.py,v 1.12 2004/04/22 19:08:47 edahl Exp $"""

__version__ = "$Revision: 1.12 $"[11:-2]

from Globals import InitializeClass
from Globals import DTMLFile

from AccessControl import ClassSecurityInfo

from Products.CMFCore import permissions

from Products.ZenModel.DeviceOrganizer import DeviceOrganizer


def manage_addLocation(context, id, description = "", REQUEST = None):
    """make a Location"""
    loc = Location(id, description)
    context._setObject(id, loc)
    loc.description = description
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 


addLocation = DTMLFile('dtml/addLocation',globals())



class Location(DeviceOrganizer):
    """
    Location is a DeviceGroup Organizer that manages physical device Locations.
    """

    # Organizer configuration
    dmdRootName = "Locations"
    dmdSubRel = "sublocations"

    portal_type = meta_type = 'Location'
    

    factory_type_information = ( 
        { 
            'id'             : 'Location',
            'meta_type'      : 'Location',
            'description'    : """Class representing arbitrary locations""",
            'icon'           : 'Location_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addLocation',
            'immediate_view' : 'viewLocationOverview',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewLocationOverview'
                , 'permissions'   : (
                  permissions.View, )
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'locationEvents'
                , 'permissions'   : (
                  permissions.View, )
                },
                { 'id'            : 'historyEvents'
                , 'name'          : 'History'
                , 'action'        : 'locationHistoryEvents'
                , 'permissions'   : (
                  permissions.View, )
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (
                  permissions.View, )
                },
            )
          },
        )

    security = ClassSecurityInfo()

    security.declareProtected('View', 'getAllCounts')
    def getAllCounts(self):
        """aggrigate ping status for all devices in this group and below"""
        return DeviceOrganizer.getAllCounts(self, "sublocations")
        

    security.declareProtected('View', 'countDevices')
    def countDevices(self):
        """count all devices with in a location"""
        count = self.devices.countObjects()
        for loc in self.sublocations():
            count += loc.countDevices()
        return count


    def pingStatus(self):
        """aggrigate ping status for all devices in this group and below"""
        return DeviceOrganizer.pingStatus(self, "sublocations")

    
    def snmpStatus(self):
        """aggrigate snmp status for all devices in this group and below"""
        return DeviceOrganizer.snmpStatus(self, "sublocations")


    def getSubDevices(self, filter=None):
        """get all the devices under and instance of a DeviceGroup"""
        return DeviceOrganizer.getSubDevices(self, filter, "sublocations")


    #need to decuple these two methods out to actions
    security.declareProtected('View', 'locationEvents')
    def locationEvents(self):
        """get the event list of this object"""
        self.REQUEST.set('ev_whereclause', "Location like '%s.*'" %
                                    self.getOrganizerName())
        return self.viewEvents(self.REQUEST)


    security.declareProtected('View', 'locationHistoryEvents')
    def locationHistoryEvents(self):
        """get the history event list of this object"""
        self.REQUEST.set('ev_whereclause', "Location like '%s%%'" %
                                    self.getOrganizerName())
        self.REQUEST.set('ev_orderby', "LastOccurrence desc")
        return self.viewHistoryEvents(self.REQUEST)


InitializeClass(Location)
