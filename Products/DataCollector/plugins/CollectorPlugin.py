#################################################################
#
#   Copyright (c) 2005 Confmon Corporation. All rights reserved.
#
#################################################################

import re
import struct

import Products.ZenUtils.IpUtil as iputil

from DataMaps import ObjectMap, RelationshipMap

class CollectorPlugin:
    """

    """

    order = 100
    transport = ""
    maptype = ""
    relname = ""
    compname = ""
    modname = ""
    classname = ""

    isip = iputil.isip

    _prepId = re.compile(r'[^a-zA-Z0-9-_,.$ ]').sub
    _cleanend = re.compile(r"_+$").sub
    def prepId(self, id):
        """Make an id with valid url characters. Subs [^a-zA-Z0-9-_~,.$\(\)# ]
        with "_".  If id then starts with "_" it is removed.
        """
        id = self._prepId("_", id)
        if id.startswith("_"):
            if len(id) > 1: id = id[1:]
            else: id = "-"
        id = self._cleanend("",id)
        return id


    def maskToBits(self, mask):
        """Return the netmask as number of bits 255.255.255.0 -> 24.
        """
        return iputil.maskToBits(mask)


    def objectMap(self, data={}):
        om = ObjectMap(data)
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

    
    def preprocess(self, results, log):
        """Perform any plugin house keeping before calling user func process.
        """
        return results


    def process(self, device, results, log):
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
    conditionOids = []
    snmpGetMap = None
    snmpGetTableMaps = []


    def condition(self, device, log):
        """Default snmp condition is true but it can be overridden.
        Default test is to check for condition oids.
        """
        return True


    def preprocess(self, results, log):
        getdata, tabledatas = results
        if self.snmpGetMap:
            getdata = self.snmpGetMap.mapdata(getdata)
        tdata = {}
        for tmap, tabledata in tabledatas.items():
           tdata[tmap.name] = tmap.mapdata(tabledata)
        return (getdata, tdata)



    def asmac(self, val):
        """Convert a byte string to a mac address string.
        """
        mac = []
        for char in val:
            tmp = struct.unpack('B', char)[0]
            tmp =  str(hex(tmp))[2:]
            if len(tmp) == 1: tmp = '0' + tmp
            mac.append(tmp)
        return ":".join(mac).upper()


    def asip(self, val):
        """Convert a byte string to an ip address string.
        """
        return ".".join(map(str, struct.unpack('!4B', char)))
    

    def asdate(self,val):
        """Convert a byte string to the date string 'YYYY/MM/DD HH:MM:SS'
        """
        datear = (1968,1,8,10,15,00)
        try:
            datear = struct.unpack("!h5B", val[0:7])
        except: pass
        if datear[0] == 0:
            datear = (1968,1,8,10,15,00)
        return "%d/%02d/%02d %02d:%02d:%02d" % datear[:6]

        

        
class GetMap(object):
    """
    Map oids in a get to their names.
    """

    def __init__(self, oidmap):
        self.oidmap = oidmap


    def getoids(self):
        return self.oidmap.keys()


    def mapdata(self, results):
        data = {}
        for oid, value in results.items():
            data[self.oidmap[oid]] = value
        return data

            
    
class GetTableMap(object):
    """
    Map snmp table oids to their column names.
    """
    
    def __init__(self, name, tableoid, colmap):
        self.name = name
        self.tableoid = tableoid
        self.colmap = colmap
        self._oids = {}
        for numb, name in self.colmap.items():
            self._oids[self.tableoid+numb] = name


    def getoids(self):
        """Return the raw oids used to get this table.
        """
        return self._oids.keys()


    def mapdata(self, results):
        """Map data from format return by table get (which is column based)
        to row based format data[rowidx][colname].
        """
        data = {}
        for col, rows in results.items():
            name = self._oids[col]
            clen = len(col)+1
            for roid, value in rows.items():
                ridx = roid[clen:]
                data.setdefault(ridx, {})
                data[ridx][name] = value
        return data
        
            

class HttpPlugin(CollectorPlugin):
    """
    HttpPlugin collects info using http.
    """

    transport = "http"
    collectoids = []

