###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = '''NullConfig

Provides a blank configuration to send no proxies to the remote
collector.
'''

import logging
log = logging.getLogger('zen.HubService.NullConfig')

import Globals
from Products.ZenCollector.services.config import CollectorConfigService

class NullConfig(CollectorConfigService):
    def __init__(self, dmd, instance):
        CollectorConfigService.__init__(self, dmd, instance)

    def _filterDevices(self, deviceList):
        return []
