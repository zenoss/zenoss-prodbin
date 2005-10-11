#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""FileSystemMap

FileSystemMap maps the interface and ip tables to interface objects

$Id: HRFileSystemMap.py,v 1.2 2004/04/07 16:26:53 edahl Exp $"""

__version__ = '$Revision: 1.2 $'[11:-2]

import re

from CustomRelMap import CustomRelMap

class HRFileSystemMap(CustomRelMap):

    fsTableOid = '.1.3.6.1.2.1.25.2.3.1'
    fsMap = {
            '.1': 'snmpindex',
             '.2': 'type',
             '.3': 'mount',
             '.4': 'blockSize',
             '.5': 'totalBlocks',
             '.6': 'usedBlocks',
             }

    prepId = re.compile(r'[^a-zA-Z0-9-_~,.$\(\)# ]')

    def __init__(self):
        CustomRelMap.__init__(self, 'filesystems', 
                                'Products.ZenModel.FileSystem')



    def condition(self, device, snmpsess, log):
        """does device meet the proper conditions for this collector to run"""
        data = None
        try:
            data = snmpsess.get('.1.3.6.1.4.1.546.1.1.1.17.0')
            if data: return None
        except:pass
        try:
            data = snmpsess.get('.1.3.6.1.2.1.25.2.3.1.1.1')
        except:pass
        return data


    def collect(self, device, snmpsess, log):
        """collect snmp information from this device"""
        log.info('Collecting host resources filesystem for device %s' % device.id)
        fstable = snmpsess.collectSnmpTableMap(self.fsTableOid, self.fsMap)
        dontcollectfsnames = getattr(device, 'zFileSystemMapIgnoreNames', None)
        datamaps = []
        for fs in fstable.values():
            if ((fs['type'] != ".1.3.6.1.2.1.25.2.1.4")
                or
                fs['totalBlocks'] <= 0
                or (dontcollectfsnames 
                    and re.search(dontcollectfsnames, fs['mount']))):
                continue
            bsize = long(fs['blockSize'])
            fs['id'] = self.prepId.sub('-', fs['mount'])
            fs['totalBytes'] = long(bsize * fs['totalBlocks'])
            fs['availBytes'] = long(bsize * 
                    (fs['totalBlocks'] - fs['usedBlocks']))
            fs['usedBytes'] = long(bsize * fs['usedBlocks'])
            fs['capacity'] = "%d" % (fs['usedBytes'] / 
                                        float(fs['totalBytes']) * 100)
            del fs['totalBlocks']
            del fs['usedBlocks']
            datamaps.append(fs)
        return datamaps


