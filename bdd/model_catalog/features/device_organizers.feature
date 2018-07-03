##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


Feature: Device Organizers are indexed


Background: Connections to zodb and model catalog are available
    Given I can connect to "zodb"
    and I can connect to "model catalog"


Scenario Outline: DeviceOrganizer.getSubDevices returns accurate information
    Given all "DeviceOrganizers" have been indexed
    When I search for all devices in "<DEVICE_ORGANIZER>" using getSubDevices
    Then I get all the devices available in "<DEVICE_ORGANIZER>"

    Examples:
        |         DEVICE_ORGANIZER          |
        |    /zport/dmd/Devices             |
        |  /zport/dmd/Devices/Server        |
        |  /zport/dmd/Devices/Server/Linux  |