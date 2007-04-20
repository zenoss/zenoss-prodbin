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
__doc__="""BatchDeviceLoader.py

BatchDeviceLoader.py loads a list of devices read from a file.
The file can be formatted like this:

device0
/Path/To/Device
device1
device2
/Path/To/Other
    device3
    device4"""

import Globals
import transaction
import re
import sys

from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.CmdBase import CmdBase


class BatchDeviceLoader(ZCmdBase):

    def __init__(self):
        ZCmdBase.__init__(self)
        #self.dmd = ZCmdBase().dmd
        self.loader = self.dmd.DeviceLoader

    def loadDevices(self):
        data = open(self.options.infile,'r').read()
        device_list = self.parseDevices(data)
        while device_list:
            device = device_list.pop()
            if device['deviceName']:
                self.log.info("Attempting to load %s" % device['deviceName'])
                self.loader.loadDevice(**device)

    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('-i', '--infile',
            dest="infile", default="",
            help="input file for import (default stdin)")

    def parseDevices(self, rawDevices):
        _slash = re.compile(r'\s*/', re.M)
        _sp = re.compile(r'\s+', re.M)
        _r = re.compile(r'\s+/', re.M)
        if not _slash.match(rawDevices): 
            rawDevices = "/Discovered\n" + rawDevices
        sections = [re.split(_sp, x) for x in re.split(_r, rawDevices)]
        finalList = []
        for s in sections:
            path, devs = s[0], s[1:]
            if not path.startswith('/'): path = '/' + path
            finalList += [{'deviceName':x,'devicePath':path} for x in devs]
        return finalList

if __name__=='__main__':
    b = BatchDeviceLoader()
    b.loadDevices()
