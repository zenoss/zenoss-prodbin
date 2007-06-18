#!/usr/bin/python
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

#
# Contained below is a convenience file for calling all tests.
#
# Adam Modlin and Nate Avers
#

import unittest


loader = unittest.TestLoader()
runner = unittest.TextTestRunner(verbosity = 2) # Enables detailed output.

testAll = loader.loadTestsFromNames(["TestDeviceInstance.TestDeviceInstanceOsTab",
                                     "TestDeviceInstance.TestDeviceInstanceManageDevice",
                                     "TestDevices.TestDevices",
                                     "TestEvents.TestEvents",
                                     "TestGroups.TestGroups",
                                     "TestLocations.TestLocations",
                                     "TestReports.TestReports",
                                     "TestSystems.TestSystems"
                                     "TestEventManager.TestEventManager"])
                                     
result = runner.run(testAll)
