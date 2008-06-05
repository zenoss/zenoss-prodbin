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

__doc__ = "Manage ZenPack-provided daemons"

import Globals
import os
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.ZenModel.ZenPack import ZenPackException


def NameZenPackDaemons(dmd, zenPackId=None):
    """
    Return a list of the names of the daemons provided by the given ZenPack.  
    If no ZenPack is specified then list all daemons provided by all ZenPacks.
    """
    from Products.ZenModel.ZenPackLoader import ZPLDaemons
    dList = []
    if zenPackId:
        objectIds = [zenPackId]
    else:
        objectIds = dmd.ZenPackManager.packs.objectIds()
    for zpId in objectIds:
        try:
            zp = dmd.ZenPackManager.packs._getOb(zpId)
        except AttributeError:
            continue
        dList += ZPLDaemons().list(zp, None)
    return dList


class ZenPackDaemons(ZenScriptBase):
    """
    Utilities for handling ZenPack-provided daemons
    """

    def run(self):
        """
        Execute the user's request.
        """
        self.connect()

        if self.options.list:
            dList = NameZenPackDaemons(self.dmd)
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
    try:
        zp = ZenPackDaemons()
        zp.run()
    except ZenPackException, e:
        sys.stderr.write('%s\n' % str(e))
        sys.exit(-1)
