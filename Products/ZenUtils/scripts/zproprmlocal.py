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
#! /usr/bin/env python 
__doc__ = "Remove local value of zProperty from Devices"

import Globals
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Acquisition import aq_base
import transaction
import sys

class ZPropRmLocal(ZCmdBase):
    "Remove local value of zProperty from Devices"

    def run(self):
        msg = []
        
        if not self.options.deviceClass:
            msg.append('You must specify a device class with the'
                        ' --class option.')
        
        if not self.options.zPropName:
            msg.append('You must specify a zProperty name with the'
                        ' --zproperty option.')
                        
        if msg:
            print('\n'.join(msg))
            sys.exit(0)
        
        try:
            devClass = self.dmd.Devices.getOrganizer(self.options.deviceClass)
        except KeyError:
            print('Unable to locate device class %s' % 
                                self.options.deviceClass)
            sys.exit(0)
        
        devs = []
        if self.options.recurse:
            devList = devClass.getSubDevicesGen()
        else:
            devList = devClass.devices()
        for dev in devList:
            if hasattr(aq_base(dev), self.options.zPropName):
                dev._delProperty(self.options.zPropName)
                devs.append(dev)

        transaction.commit()

        print('Deleted %s from %s devices.' % (
                            self.options.zPropName, len(devs)))
        for d in devs:
            sys.stdout.write(d.getPrimaryId())
            

    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('--class',
                               dest='deviceClass',
                               default='/',
                               help="Device class to operate on")
        self.parser.add_option('--zproperty',
                               dest='zPropName',
                               default=None,
                               help="Name of the zProperty to remove from"
                                    " devices")
        self.parser.add_option('-r', '--recurse',
                               dest='recurse',
                               action="store_true",
                               default=False,
                               help="Recurse into subclasses of --class")

if __name__ == '__main__':
    zp = ZPropRmLocal()
    zp.run()
