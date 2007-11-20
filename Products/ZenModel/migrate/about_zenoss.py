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

Create the directories on the file system necessary for importing and exporting
templates to and from Zenoss.

'''

__version__ = "$Revision$"[11:-2]

from Products.ZenModel.ZenossInfo import manage_addZenossInfo

import Migrate

class AboutZenoss(Migrate.Step):
    version = Migrate.Version(0, 23, 0)

    def cutover(self, dmd):
        if hasattr(dmd.zport, 'ZenossInfo'):
            dmd.zport._delObject('ZenossInfo')
        if not hasattr(dmd,'About'):
            manage_addZenossInfo(dmd)

AboutZenoss()
