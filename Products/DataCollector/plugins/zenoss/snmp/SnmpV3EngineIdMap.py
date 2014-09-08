##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """SnmpV3EngineIdMap

Map SNMP v3 Engine id info
"""

from Products.DataCollector.plugins.CollectorPlugin import SnmpPlugin, GetMap
import binascii

class SnmpV3EngineIdMap(SnmpPlugin):

    snmpGetMap = GetMap({'.1.3.6.1.6.3.10.2.1.1.0': 'setSnmpV3EngineId'})

    def condition(self, device, log):
        """ Only for snmp v3 and if we do not have a value for zSnmpEngineId """
        return ('3' in device.zSnmpVer and len(device.zSnmpEngineId) == 0)

    def process(self, device, results, log):
        """ collect snmp information from this device """
        log.info('Processing %s for device %s', self.name(), device.id)
        getdata, tabledata = results
        om = self.objectMap(getdata)
        om.setSnmpV3EngineId = binascii.hexlify(om.setSnmpV3EngineId)
        return om
