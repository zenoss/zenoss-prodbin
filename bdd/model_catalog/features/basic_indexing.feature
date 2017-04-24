##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


Feature: Basic Zodb data is indexed


Background: Connections to zodb and model catalog are available
    Given I can connect to "zodb"
    and I can connect to "model catalog"


Scenario Outline: All relevant zodb objects are indexed
    Given all "<OBJECT_TYPE>" have been indexed
    When I search for all "<OBJECT_TYPE>" in model catalog
    Then I get all the "<OBJECT_TYPE>" available in Zenoss

    Examples:
        |     OBJECT_TYPE     |
        |   device classes    |
        |    event classes    |
        |       groups        |
        |      locations      |
        |       systems       |
        |    manufacturers    |
        |    mib organizers   |
        |         mibs        |
        |    RRD templates    |
        |  process organizers |
        |      processes      |
        |   report organizers |
        |       reports       |
        |       services      |
        |       devices       |
