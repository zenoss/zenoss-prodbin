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
from ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import *


class Linkable:
    """ A mixin allowing an object to be the 
        endpoint of a Link object.
    """

    meta_type = "Linkable"

    _relations = (
        ("links", ToMany(ToMany, "Products.ZenModel.Link", "endpoints")),
    )

    def getEndpointName(self):
        """ Returns a unique endpoint name """
        pass

    def isInLocation(self, context):
        """ Checks if Linkable is in given Location """
        pass

    def unlink(self):
        """ Removes all links associated with a Linkable """
        zlm = dmd.ZenLinkManager
        for link in self.links():
            zlm.manage_removeLink(link.id)


InitializeClass(Linkable)
