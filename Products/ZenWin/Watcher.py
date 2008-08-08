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
from Products.ZenWin.WMIClient import WMIClient

import logging
log = logging.getLogger('zen.Watcher')

class Watcher:

    def __init__(self, device, query):
        wmic = WMIClient(device)
        wmic.connect()
        log.debug('Starting watcher')
        self.watcher = wmic.watcher(query)
        log.debug('Watcher started')

    def nextEvent(self, timeout=0):
        log.debug('calling next event')
        try:
            return self.watcher.nextEvent(timeout)
        finally:
            log.debug('next event returned')

    def close(self):
        del self.watcher
