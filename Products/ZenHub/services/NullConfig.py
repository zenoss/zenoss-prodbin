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
