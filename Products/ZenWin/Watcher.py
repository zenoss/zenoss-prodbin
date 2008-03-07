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

def debug(msg):
    pass
    # import sys
    # sys.stderr.write(msg + '\n')

class Watcher:

    def __init__(self, device, query):
        wmic = WMIClient(device)
        wmic.connect()
        debug('Starting watcher')
        self.watcher = wmic.watcher(query)
        debug('Watcher started')

    def nextEvent(self, timeout=0):
        import Query
        debug('calling next event')
        try:
            return Query.picklable(self.watcher.nextEvent(timeout))
        finally:
            debug('next event returned')

