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


from Globals import InitializeClass
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.Utils import unused


class ILink(object):
    """ Defines the interface for Link-like objects, which
        represent a connection between two devices or components 
    """

    link_type = ''
    OSI_layer = '' 
    entry_type = ''

    def getStatus(self):
        """ Returns the event status, determined by:
                Pingdown on Device owning either endpoint
                Most severe event on either endpoint
        """
        raise NotImplementedError

    def setEndpoints(self, pointa, pointb):
        """ Sets the two endpoints of a link-like object """
        raise NotImplementedError

    def getEndpointNames(self):
        """ Returns unique endpoint names (see Linkable.getEndpointName)"""
        raise NotImplementedError

    def getOtherEndpoint(self, endpoint):
        """ Returns the link endpoint that is not the one given """
        raise NotImplementedError

    def getDataForJSON(self):
        """ Returns data ready for serialization.
            Format:
                [ id link as string 
                , endpoint a name 
                , endpoint b name 
                , self.OSI_layer 
                , self.link_type 
                , self.entry_type
                , self.id
                ]
        """
        raise NotImplementedError

    def getGeomapData(self, context, full=False):
        """ Return the addresses of the endpoints
            aggregated for the generation of the context
        """
        raise NotImplementedError



class Link(ZenModelRM, ILink):
    """ A link between two Linkable objects,
        which can have a status and a type.
        Implements ILink interface.
    """

    link_type = ''
    OSI_layer = "1"
    entry_type = 'manual'

    default_catalog = 'linkSearch'

    _properties = ZenModelRM._properties + (
        {'id':'link_type','type':'string','mode':'w'},
        {'id':'OSI_layer', 'type':'string', 'mode':'w'},
        {'id':'entry_type', 'type':'string', 'mode':'w'},
    )

    _relations = (
        ("endpoints", 
            ToMany(ToMany, "Products.ZenModel.Linkable", "links")),
        ("linkManager", 
            ToOne(ToManyCont, "Products.ZenModel.LinkManager", "links")),
    )
    
    factory_type_information = (
        { 'immediate_view' : 'editLink',
          'factory'        : 'manage_addLink',
          'actions'        :
          (
           { 'id'            : 'editLink'
             , 'name'          : 'Edit'
             , 'action'        : 'editLink'
             , 'permissions'   : ( "Manage DMD", )
             },
           )
          },
        )

    def __init__(self, id):
        self.id = id
        ZenModelRM.__init__(self, id)
        self.buildRelations()

    def manage_afterAdd(self, item, container):
        unused(item, container)
        self.index_object()

    def manage_beforeDelete(self, item, container):
        unused(item, container)
        self.unindex_object()

    def setEndpoints(self, pointa, pointb):
        self.endpoints._setObject(pointa.id, pointa)
        self.endpoints._setObject(pointb.id, pointb)

    def getEndpointNames(self):
        return [x.getEndpointName() for x in self.endpoints()]

    def getOtherEndpoint(self, endpoint):
        """ Return the link endpoint that is not the one given """
        eps = self.endpoints()
        if eps[0]==endpoint: 
            return eps[1]
        return eps[0]

    def getDataForJSON(self):
        """ returns data ready for serialization
        """
        id = '<a class="tablevalues" href="%s">%s</a>' % (
                            self.absolute_url_path(), self.getId())
        pointa, pointb = self.getEndpointNames()
        link_type = self.link_type
        entry_type = self.entry_type
        OSI_layer = self.OSI_layer
        return [id, pointa, pointb, OSI_layer, link_type, entry_type,
                self.getId()]

    def getStatus(self):
        """ Status of link is determined by:
                Pingdown on Device owning either endpoint
                Most severe event on either endpoint
        """
        eps = self.endpoints()
        if max([ep.device().getPingStatus() for ep in eps]) > 0:
            return 5
        zem = self.dmd.ZenEventManager
        return max(map(zem.getMaxSeverity, eps))

    def getGeomapData(self, context, full=False):
        """ Return the addresses of the endpoints
            aggregated for the generation of the context
        """
        generation = len(context.getPrimaryPath())
        def getancestoraddress(endpoint):
            loc = endpoint.device().location()
            path = loc.getPrimaryPath()
            path = '/'.join(path[:generation])
            ancestor = self.dmd.getObjByPath(path)
            if full:
                return ancestor.getGeomapData()
            else:
                return ancestor.address
        result = map(getancestoraddress, self.endpoints())
        if result[0]==result[1]: return None
        result.sort()
        return tuple(result)



InitializeClass(Link)
