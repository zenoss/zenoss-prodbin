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

__doc__='''

Add link relations to all IpInterfaces.
Create a LinkManager object on the dmd.

'''
import Migrate
from Products.ZenRelations.ImportRM import ImportRM
from Products.ZenModel.LinkManager import manage_addLinkManager
from Products.ZenModel.Linkable import Linkable
from Products.ZenUtils.Utils import cmpClassNames


class Linkability(Migrate.Step):
    version = Migrate.Version(2, 1, 0)

    def cutover(self, dmd):

       # Create a LinkManager if one does not exist
        if not hasattr(dmd, 'ZenLinkManager'):
            manage_addLinkManager(dmd)

        # Build relations on all Linkable components
        for component in dmd.Devices.getSubComponents():
                if isinstance(component, Linkable):
                    component.buildRelations()

Linkability()
