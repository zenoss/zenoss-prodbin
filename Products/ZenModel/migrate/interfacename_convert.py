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

__doc__='''

change attribute name in interface to interfaceName because it
conflicts with name function of DeviceClass

'''

__version__ = "$Revision$"[11:-2]

import Migrate

from Acquisition import aq_base

import os

class InterfaceNameConvert(Migrate.Step):
    version = Migrate.Version(0, 21, 0)

    def cutover(self, dmd):
        for dev in dmd.Devices.getSubDevices():
            for int in dev.os.interfaces():
                interfaceName = getattr(aq_base(int), 'name', None)
                if interfaceName is not None and not callable(interfaceName):
                    int.interfaceName = interfaceName
                    delattr(int, 'name')
        try:
            dmd.Devices.reIndex()
        except AttributeError:
            pass
        if hasattr(aq_base(dmd.Devices), "interfaceSearch"):
            dmd.Devices._delObject("interfaceSearch")


InterfaceNameConvert()
