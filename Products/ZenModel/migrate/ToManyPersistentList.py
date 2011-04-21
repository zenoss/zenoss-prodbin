###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__="""
Changes all of the ToManyRelationships to be persistent lists instead of
regular python lists.
This results in performance improvements when accessing the objects
"""

import Migrate

class ToManyPersistentList(Migrate.Step):
    version = Migrate.Version(3, 1, 70)

    def cutover(self, dmd):
        root = dmd.Services
        # migrate services
        for org in root.getSubOrganizers():
            for svcclass in org.serviceclasses():
                svcclass.instances.convertToPersistentList()

        # device organizers
        for root in (dmd.Groups, dmd.Systems, dmd.Locations):
            for org in root.getSubOrganizers():
                org.devices.convertToPersistentList()

ToManyPersistentList()

