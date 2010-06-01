###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, 2009 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """zenpackdaemons
Manage ZenPack-provided daemons
"""

import os

import Globals
from Products.ZenUtils.PkgResources import pkg_resources

from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.ZenUtils.ZenPackCmd import ZENPACK_ENTRY_POINT
from Products.ZenModel.ZenPackLoader import ZPLDaemons
from Products.ZenUtils.Utils import zenPath


class ZenPackDaemons(ZenScriptBase):
    """
    Utilities for handling ZenPack-provided daemons
    """

    def nameZenPackDaemons(self, zenPackId=None):
        """
        Return a list of the names of the daemons provided by the given ZenPack.  
        If no ZenPack is specified then list all daemons provided by all ZenPacks.
        """
        dList = []
        zpl = ZPLDaemons()
        # Get daemons from egg-based ZenPacks
        for entry in pkg_resources.iter_entry_points(ZENPACK_ENTRY_POINT):
            try:
                module = entry.load()
                dList += zpl.list(os.path.dirname(module.__file__), None)
            except Exception, ex:
                summary = "The ZenPack %s cannot be imported -- skipping." % entry.name
                self.log.exception(summary)

        # Get daemons from non-egg ZenPacks
        prodDir = zenPath('Products')
        for item in os.listdir(prodDir):
            if not item.startswith('.'):
                dList += zpl.list(os.path.join(prodDir, item), None)
        return dList


    def run(self):
        """
        Execute the user's request.
        """

        if self.options.list:
            dList = self.nameZenPackDaemons()
            if dList:
                print '\n'.join(dList)
        else:
            self.parser.print_help()


    def buildOptions(self):
        self.parser.add_option('--list',
                               dest='list',
                               default=False,
                               action='store_true',
                               help='List the names of ZenPack-supplied daemons'
                               )
        ZenScriptBase.buildOptions(self)


if __name__ == '__main__':
    zp = ZenPackDaemons()
    zp.run()
