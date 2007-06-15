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

#from selTestBase import selTestBase

import testDeviceInstance
import testDevices
import testEvents
import testGroups
import testLocations
import testReports
import testSystems


loader = unittest.TestLoader()
runner = unittest.TextTestRunner(verbosity = 2)

testAll = loader.loadTestsFromNames(["testDeviceInstance.DeviceInstanceTest",
                                     "testDevices.DevicesTest",
                                     "testEvents.EventsTest",
                                     "testGroups.GroupsTest",
                                     "testLocations.LocationsTest",
                                     "testReports.ReportsTest",
                                     "testSystems.SystemsTest"])
                                     
result = runner.run(testAll)

        
#if __name__ == "__main__":
#    unittest.main()