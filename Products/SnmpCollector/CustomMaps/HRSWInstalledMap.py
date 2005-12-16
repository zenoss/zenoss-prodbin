#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""FileSystemMap

FileSystemMap maps the interface and ip tables to interface objects

$Id: HRSWInstalledMap.py,v 1.2 2004/04/07 16:26:53 edahl Exp $"""

__version__ = '$Revision: 1.2 $'[11:-2]

import re

from CustomRelMap import CustomRelMap

class HRSWInstalledMap(CustomRelMap):

    swTableOid = '.1.3.6.1.2.1.25.6.3.1'
    swMap = {
            '.1': 'snmpindex',
             '.2': 'setProductKey',
             #'.4': 'type',
             #'.5': 'setInstallDate',
             }

    prepId = re.compile(r'[^a-zA-Z0-9-_~,.$\(\)# ]')

    def __init__(self):
        CustomRelMap.__init__(self, 'software', 
                                'Products.ZenModel.Software')



    def condition(self, device, snmpsess, log):
        """does device meet the proper conditions for this collector to run"""
        data = None
        try:
            data = snmpsess.get('.1.3.6.1.2.1.25.6.3.1.1.1')
        except:pass
        return data


    def collect(self, device, snmpsess, log):
        """collect snmp information from this device"""
        log.info('Collecting host resources software for device %s' % device.id)
        swtable = snmpsess.collectSnmpTableMap(self.swTableOid, self.swMap)
        datamaps = []
        for sw in swtable.values():
            sw['id'] = self.prepId.sub('_', sw['setProductKey'])
#            if sw['setInstallDate']:
#                log.info("installdate=",sw['setInstallDate'])
#                date, time = sw['setInstallDate'].split(",")[:2]
#                date = date.replace("-", "/")
#                time = ":".join(map(lambda x: "%02d" % int(x), time.split(":")))
#                sw['setInstallDate'] = "%s %s" % (date, time)        
            datamaps.append(sw)
        return datamaps


