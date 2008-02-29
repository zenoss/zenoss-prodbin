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

import Globals
from WMIC import WMIClient

class Watcher:

    def __init__(self, device, query):
        wmic = WMIClient(device)
        wmic.connect()
        self.watcher = wmic.watcher(query)

    def nextEvent(self, timeout=0):
        import Query
        return Query.picklable(self.watcher.nextEvent(timeout))

