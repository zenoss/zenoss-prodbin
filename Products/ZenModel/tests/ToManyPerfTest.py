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

import Zope2
app = Zope2.app()

from Products.ZenModel.IpInterface import manage_addIpInterface

class PerfTest:

    def __init__(self, app, nints):
        self.dc = app.zport.dmd.Devices
        self.nints = nints

    def create(self):
        device = self.getdev()
        for i in range(self.nints):
            intname = "hme%03d" % i
            manage_addIpInterface(device.interfaces, intname)

    def testints(self):
        for i in range(self.nints):
            intname = "tint%03d" % i
            manage_addIpInterface(self.dc, intname)


    def linkints(self):
        device =  self.getdev()
        for i in range(self.nints):
            intname = "tint%03d" % i
            intobj = self.dc._getOb(intname)
            device.addRelation('interfaces', intobj)


    def delints(self):
        for i in range(self.nints):
            intname = "tint%03d" % i
            self.dc._delObject(intname)


    def rcall(self):
        device = self.getdev()
        for int in device.interfaces():
            n = int.id


    def objvall(self):
        device = self.getdev()
        for int in device.interfaces.objectValuesAll():
            n = int.id


    def objv(self):
        device = self.getdev()
        for int in device.interfaces.objectValues():
            n = int.id


    def deldev(self):
        self.dc._delObject('testdev')
        

    def getdev(self):
        device = self.dc._getOb('testdev', None)
        if not device:
            device = self.dc.createInstance('testdev')
        return device


pt = PerfTest(app, 1000)
