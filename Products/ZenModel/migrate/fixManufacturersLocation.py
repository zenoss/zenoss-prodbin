###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__='''

'''
import Globals
import Migrate
from Acquisition import aq_base


class FixManufacturersLocation(Migrate.Step):
    """
    There was a bug with the 2.1.90 Manufacturers xml.  Manufacturers were
    loaded into the dmd rather than dmd.Manufacturers.  This migrate step
    looks for Manufacturers in dmd and moves them to Manufacturers.  If the
    same manufacturer already exists there then the one in dmd is just
    removed.
    """
    version = Migrate.Version(2, 2, 0)


    def cutover(self, dmd):
        for m in dmd.objectValues('Manufacturer'):
            dmd._delObject(m.id)
            m = aq_base(m)
            if not dmd.Manufacturers._getOb(m.id, None):
                dmd.Manufacturers._setObject(m.id, m)


fixManufacturersLocation = FixManufacturersLocation()
