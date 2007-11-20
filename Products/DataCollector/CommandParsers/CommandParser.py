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

__doc__ = """CommandParser

CommandParser parses the output of a command to return a datamap

$Id: CommandParser.py,v 1.1 2003/09/25 16:21:52 edahl Exp $"""

__version__ = '$Revision: 1.1 $'[11:-2]

from Products.DataCollector.ObjectMap import ObjectMap
from Products.DataCollector.RelationshipMap import RelationshipMap

from Products.ZenUtils.Utils import prepId as globalPrepId

class CommandParser:

    #Subclasses must fill this in with appropriate command
    command = ''
   
    def prepId(self, id, subchar='_'):
        return globalPrepId(id, subchar)

    def newObjectMap(self, className=None):
        return ObjectMap(className)

    def newRelationshipMap(self, relationshipName, componentName=""):
        return RelationshipMap(relationshipName, componentName)
        
    def condition(self, device, snmpsess):
        """does device meet the proper conditions for this collector to run"""
        return 0


    def parse(self, results, log):
        """collect snmp information from this device
        device is the a Device class (or subclass) object
        snmpsess is a valid instance of SnmpSession to connect
        to this device"""
        pass


    def description(self):
        """return a description of what this map does"""
        pass
