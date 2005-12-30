#################################################################
#
#   Copyright (c) 2005 Confmon Corporation. All rights reserved.
#
#################################################################

import re

import Products.ZenUtils.IpUtil as iputil

from DataMaps import ObjectMap, RelationshipMap

class CollectorPlugin:
    """

    """

    transport = ""
    maptype = ""
    relname = ""
    compname = ""
    modname = ""
    classname = ""

    isip = iputil.isip    

    _prepid = re.compile(r'[^a-zA-Z0-9-_~,.$\(\)# ]').sub

    def prepId(self, id):
        """Make an id with valid url characters. Subs [^a-zA-Z0-9-_~,.$\(\)# ]
        with "_".  If id then starts with "_" it is removed.
        """
        id = self._prepid("_", id)
        if id.startswith("_"):
            if len(id) > 1: id = id[1:]
            else: id = "-"
        return id


    def maskToBits(self, mask):
        """Return the netmask as number of bits 255.255.255.0 -> 24.
        """
        return iputil.maskToBits(mask)


    def objectMap(self):
        om = ObjectMap()
        om.compname = self.compname
        om.modname = self.modname
        om.classname = self.classname
        return om


    def relMap(self):
        relmap = RelationshipMap()
        relmap.relname = self.relname
        relmap.compname = self.compname
        return relmap
       

    def condition(self, device, log):
        """Test to see if this CollectorPlugin is valid for this device.
        """
        raise NotImplementedError

    
    def process(self, results, log):
        """Process the data this plugin collects.
        """
        raise NotImplementedError


    def name(self):
        """Return the name of this plugin.
        """
        return self.__class__.__module__.replace("plugins.","")


class CommandPlugin(CollectorPlugin):
    """
    A CommandPlugin defines a command to be run on a remote device and
    a parsing methos to turn the commands output into a datamap.  A valid
    CommandPlugin must have class variable "command" defined and must implement
    the methods process and condition.
    """
    transport = "command"
    command = ""



class SnmpPlugin(CollectorPlugin):
    """
    An SnmpPlugin defines a mapping from snmp mib values to a datamap. 
    A valid SnmpPlugin must define collectoids a list of oids to be collected
    and the process method which converts the oid data to a datamap.  It
    can override the condition method if nessesary.
    """

    transport = "snmp"
    collectoids = []

    def condition(self, device, log):
        """Test for the the collect oids.
        """
        pass #FIXME - implement me


class HttpPlugin(CollectorPlugin):
    """
    HttpPlugin collects info using http.
    """

    transport = "http"
    collectoids = []

