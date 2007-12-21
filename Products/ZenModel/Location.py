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

__doc__="""Location

$Id: Location.py,v 1.12 2004/04/22 19:08:47 edahl Exp $"""

__version__ = "$Revision: 1.12 $"[11:-2]

from Globals import InitializeClass
from Globals import DTMLFile

from AccessControl import ClassSecurityInfo

from AccessControl import Permissions as permissions

from Products.ZenRelations.RelSchema import *

from DeviceOrganizer import DeviceOrganizer
from ZenPackable import ZenPackable

def manage_addLocation(context, id, description = "", 
                       address="", REQUEST = None):
    """make a Location"""
    loc = Location(id, description)
    context._setObject(id, loc)
    loc.description = description
    loc.address = address
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() +'/manage_main') 


addLocation = DTMLFile('dtml/addLocation',globals())


class Location(DeviceOrganizer, ZenPackable):
    """
    Location is a DeviceGroup Organizer that manages physical device Locations.
    """

    # Organizer configuration
    dmdRootName = "Locations"

    address = '' 

    portal_type = meta_type = event_key = 'Location'
    
    _properties = DeviceOrganizer._properties + (
        {'id':'address','type':'string','mode':'w'},
    )

    _relations = DeviceOrganizer._relations + ZenPackable._relations + (
        ("devices", ToMany(ToOne,"Products.ZenModel.Device","location")),
        ("networks", ToMany(ToOne,"Products.ZenModel.IpNetwork","location")),
    )

    # Screen action bindings (and tab definitions)
    factory_type_information = (
        {
            'immediate_view' : 'deviceOrganizerStatus',
            'actions'        :
            (
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'deviceOrganizerStatus'
                , 'permissions'   : (permissions.view,)
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'viewEvents'
                , 'permissions'   : (permissions.view,)
                },
#                { 'id'            : 'historyEvents'
#                , 'name'          : 'History'
#                , 'action'        : 'viewHistoryEvents'
#                , 'permissions'   : (permissions.view,)
#                },
                { 'id'            : 'manage'
                , 'name'          : 'Administration'
                , 'action'        : 'deviceOrganizerManage'
                , 'permissions'   : ('Manage DMD',)
                },
                { 'id'            : 'geomap'
                , 'name'          : 'Map'
                , 'action'        : 'locationGeoMap'
                , 'permissions'   : (permissions.view,)
                },
            )
         },
        )

    security = ClassSecurityInfo()

    def getChildLinks(self):
        """ Returns child link data ready for GMaps """
        return self.dmd.ZenLinkManager.getChildLinks(self)

    def numMappableChildren(self):
        children = self.children()
        return len(
            filter(lambda x:getattr(x, 'address', None), children)
        )

    def getGeomapData(self):
        """ Returns node info ready for Google Maps """
        address = self.address
        psthresh = self.dmd.prodStateDashboardThresh
        summary = self.getEventSummary(prodState=psthresh)
        colors = 'red orange yellow green green'.split()
        color = 'green'
        for i in range(5):
            if summary[i][1]+summary[i][2]>0:
                color = colors[i]
                break
        link = self.absolute_url_path()
        linkToMap = self.numMappableChildren()
        if linkToMap: 
            link+='/locationGeoMap'
        summarytext = self.mapTooltip() # mapTooltip is a page template
        return [address, color, link, summarytext]

    def getChildGeomapData(self):
        """ Returns geomap info on child nodes """
        allnodes = []
        data = []
        children = self.children()
        allnodes.extend(children)
        data = [x.getGeomapData() for x in allnodes]
        if not data: data = [self.getGeomapData()]
        return data

    def getSecondaryNodes(self):
        """ Returns geomap info on cousin nodes that should be
            included in the view due to outside linking.
        """
        data = []
        # Short-circuit the method for now
        return data
    
InitializeClass(Location)
