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


