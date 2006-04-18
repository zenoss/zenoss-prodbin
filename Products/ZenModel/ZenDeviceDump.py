#################################################################
#
#   Copyright (c) 2005 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""ZenDeviceDump

$Id: CVServerBackup.py,v 1.1.1.1 2004/10/14 20:55:29 edahl Exp $"""

__version__ = "$Revision: 1.1.1.1 $"[11:-2]

import sys
import logging
import Globals

from Acquisition import aq_base

from Products.ZenUtils.ZCmdBase import ZCmdBase
    

class ZenDeviceDump(ZCmdBase):
    """
    Dumps Device objects one per line in the following format:
    fqdn::prodState:sys1|sys2:grp1|grp2:manufacturer:model:location:cricket
    """

    def __init__(self):
        ZCmdBase.__init__(self)
        if not self.options.outfile:
            self.outfile = sys.stdout
        else:
            self.outfile = open(self.options.outfile, 'w') 


    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZCmdBase.buildOptions(self)
        self.parser.add_option('-o', '--outfile',
                    dest="outfile",
                    help="output file for export default is stdout")


    def export(self):
        if aq_base(self.dataroot).getId() == "dmd":
            self.dataroot = self.dataroot._getOb("Devices")
        if not getattr(aq_base(self.dataroot), 'getSubDevices', False):
            print "ERROR DataRoot is not a DeviceClass Object"
            sys.exit(1)
        for device in self.dataroot.getSubDevices():
            fqdn = device.getId()
            deviceClass = device.getDeviceClassName()
            manuf = device.getManufacturerName()
            model = device.getModelName()
            location = device.getLocationName()
            systems = "|".join(device.getSystemNames())
            groups = "|".join(device.getDeviceGroupNames())
            perfMon = device.getPerformanceServerName()
            productionState = str(device.productionState)
            self.outfile.write(":".join((
                                fqdn,
                                deviceClass, 
                                productionState,
                                systems,
                                groups,
                                manuf,
                                model,
                                location,
                                perfMon,
                                ))+"\n")
            logging.info("dumped device %s", fqdn)
        #self.outfile.close()


if __name__ == '__main__':
    ex = ZenDeviceDump()
    ex.export()
