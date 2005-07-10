#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""snmp

snmp utility library to have a more sane interface than pysnmp

$Id: SnmpSession.py,v 1.16 2003/07/14 19:58:49 edahl Exp $"""

__version__ = "$Revision: 1.16 $"[11:-2]

import copy
from struct import unpack

#from pysnmp import asn1, v1, v2c
#from pysnmp import role, asynrole
#from pysnmp.compat.pysnmp2x import asn1, v1, v2c, role
from pysnmp.compat.pysnmp2x import asn1, v1
from pysnmp.proto import v2c
from pysnmp.mapping.udp import role
from pysnmp.proto.api import alpha

class SnmpSession:

    def __init__(self, host, community='public', port=161,
                 version=1, timeout=2, retries=2, callback=None):
        if version != 1 and version != 2:
            raise "SNMPVersionError", ('Unsupported SNMP protocol version: %s' 
                                        % (version,))
        self.community = community
        if version == 2:
            self.version = '2c'
        else:
            self.version = '1'
        if callback:
            self.client = asynrole.manager(callback, iface=(host, port))
        else:
            self.client = role.manager((host, port))
        self.client.timeout = timeout
        self.client.retries = retries


    def collectSnmpAttMap(self, snmpmap):
        """collect snmp information from device 
        snmpmap is an SnmpAttMap object"""
        oidmap = snmpmap.getOidMap()
        oids = oidmap.keys() 
        snmpdata =  self.get(oids)
        retdata = {}
        for oid, value in snmpdata.items():
            if snmpmap.getPropertyType(oid) == 'oidmac':
                retdata[oidmap[oid]] = self.asmac(value)
            else:
                retdata[oidmap[oid]] = value
        return retdata


    def collectSnmpTableMapClass(self, snmpmap):
        """collect and map snmp table data returns a list of dictionaries 
        which have attribute names as keys and snmp data as values
        snmpmap is an SnmpTableMap object"""
        tablemap = self.collectSnmpTable(snmpmap.tableOid)
        datamaps = []
        oidmap = snmpmap.getOidMap()
        for row in tablemap.values():
            nrow = {}
            for col in row.keys():
                if oidmap.has_key(col):
                    if snmpmap.getPropertyType(col) == 'oidmac':
                        nrow[oidmap[col]] = self.asmac(row[col])
                    elif snmpmap.getPropertyType(col) == 'oidfs':
                        nrow[oidmap[col]] = row[col].replace('/', '-')
                    else:
                        nrow[oidmap[col]] = row[col]
            datamaps.append(nrow)
        return datamaps
   

    def collectSnmpTableMap(self, tableOid, dataMap, bulk=0):
        """optimized table collection we only get the columns in datamap"""
        if bulk:
            collector = self.getBulkTable
        else:
            collector = self.getTable
        retdata = {}
        tblen = len(tableOid)
        for col in dataMap.keys():
            snmpdata = collector(tableOid + col)
            colname = dataMap[col]
            for key, data in snmpdata.items():
                rowcol = key[tblen:].split('.')
                row = '.'.join(rowcol[2:])
                if not retdata.has_key(row):
                    retdata[row] = {}
                retdata[row][colname] = data
        return retdata
            


    def collectSnmpTable(self, tableOid, bulk=0):
        """collect and snmp table based on its oid and return
        a dict of dicts with row, col as keys"""
        if bulk:
            snmpdata = self.getBulkTable(tableOid)
        else:
            snmpdata = self.getTable(tableOid)
        tblen = len(tableOid)
        tablemap = {}
        for oid, value in snmpdata.items():
            rowcol = oid[tblen:].split('.')
            col = '.'.join(rowcol[:2])
            row = '.'.join(rowcol[2:])
            if not tablemap.has_key(row):
                tablemap[row] = {}
            tablemap[row][col] = value
        return tablemap


    def asmac(self, val):
        """convert a byte string to a mac address string"""
        mac = []
        for char in val:
            tmp = unpack('B', char)[0]
            tmp =  str(hex(tmp))[2:]
            if len(tmp) == 1: tmp = '0' + tmp
            mac.append(tmp)
        return ":".join(mac)


    def asip(self, val):
        ip = ""
        for char in val:
            tmp = unpack('B', char)[0]
            ip = ip + str(tmp) + "."
        return ip[:-1]
       
 
    def snmpTableMap(self, tabledata, oidmap):
        """map the results of a full table query (as returned from 
        collectSnmpTable) the oidmap should be in the same format 
        has descripbed by snmpRowMap below
        """
        datamaps = []
        for row in tabledata.values():
            nrow = self.snmpRowMap(row, oidmap)
            datamaps.append(nrow)
        return datamaps


    def snmpRowMap(self, row, oidmap):
        """map the results of a single row from a table query
        a row map has column numbers as keys (with the .)
        and object attributes as the values.
        {'.2' : 'id', '.3' : 'type',}"""
        nrow = {}
        for col in row.keys():
            if oidmap.has_key(col):
                nrow[oidmap[col]] = row[col]
        return nrow
   

    def get(self, head_oids):
        req = eval('v' + self.version).GETREQUEST()
        return self._get(req, head_oids)


    def getnext(self, head_oids):
        req = eval('v' + self.version).GETNEXTREQUEST()
        return self._get(req, head_oids)


    def _get(self, req, head_oids):
        """get a list of oids"""
        if type(head_oids) == type(''):
            head_oids = [head_oids,]
        encoded_oids = map(asn1.OBJECTID().encode, head_oids)
        (oids, vals, rsp) = self._perfreq(req, encoded_oids)
        retval={}
        for (oid, val) in map(None, oids, vals):
            retval[oid] = val
        return retval


    def getTable(self, head_oids, bulk=0):
        """walk a list of table oids"""
        if bulk:
            return self.getBulkTable(head_oids)
        if type(head_oids) == type(''):
            head_oids = [head_oids,]
        retval = {}
        encoded_oids = map(asn1.OBJECTID().encode, head_oids)
        req = eval('v' + self.version).GETNEXTREQUEST()
        while 1:
            (oids, vals, rsp) = self._perfreq(req, encoded_oids)
            if rsp['error_status'] == 2:
                # One of the tables exceeded
                for l in oids, vals, head_oids:
                    del l[rsp['error_index']-1]
            # Exclude completed OIDs
            while 1:
                for idx in range(len(head_oids)):
                    if not asn1.OBJECTID(head_oids[idx]).isaprefix(oids[idx]):
                        # One of the tables exceeded
                        for l in oids, vals, head_oids:
                            del l[idx]
                        break
                else:
                    break

            if not head_oids: return retval

            # Print out results
            for (oid, val) in map(None, oids, vals):
                retval[oid] = val

            # BER encode next SNMP Object IDs to query
            encoded_oids = map(asn1.OBJECTID().encode, oids)

            # Update request object
            req['request_id'] = req['request_id'] + 1



    def getBulkTable(self, head_oids):
        """get a set of table oids using snmp bulk requests
        if a list of oids is passed in they must have result
        rows that are the same length (ie different columns 
        of the same table)"""
        if type(head_oids) == type(''):
            head_oids = [head_oids,]
        retdata = {}
        oids = copy.copy(head_oids)
        req = v2c.GetBulkRequest()
        req['community'].set(self.community)
        req['pdu']['get_bulk_request']['variable_bindings'].extend(
            map(lambda x: v2c.VarBind(name=v2c.ObjectName(x)), oids))
        rsp = v2c.Response();
        while 1:
            vb = map(lambda x: v2c.VarBind(name=v2c.ObjectName(x)), oids)
            req['pdu'].values()[0]['variable_bindings']=v2c.VarBindList(*vb)
            # Encode SNMP request message and try to send it to SNMP agent and
            # receive a response
            (answer, src) = self.client.send_and_receive(req.encode())
            # Attempt to decode SNMP response
            rsp.decode(answer)
            # Make sure response matches request
            if not req.match(rsp):
                raise 'Unmatched response: %s vs %s' % (req, rsp)
            # Fetch Object ID's and associated values
            oids = map(lambda x: x['name'].get(), \
                       rsp['pdu'].values()[0]['variable_bindings'])
            vals = map(lambda x: x['value'], \
                       rsp['pdu'].values()[0]['variable_bindings'])
            # Check for remote SNMP agent failure
            if rsp['pdu'].values()[0]['error_status']:
                raise str(rsp['pdu'].values()[0]['error_status']) + ' at '\
                      + str(oids[rsp['pdu'].values()[0]['error_index'].get()-1])
            # The following is taken from RFC1905 
            # (fixed not to depend of repetitions)
            N = 0;
            R = len(req['pdu'].values()[0]['variable_bindings']) - N
            L = len(rsp['pdu'].values()[0]['variable_bindings'])
            M = L / R
            cut=(R*M)-L
            if cut < 0:
                oids=oids[:cut]
                vals=vals[:cut]
            for i in range(1, M+1):
                for r in range(1, R+1):
                    idx = N + ((i-1)*R) + r
                    oid = oids[idx-1]
                    if oid.find(head_oids[r-1]) > -1: 
                        retdata[oid] =
                            vals[idx-1].apiAlphaGetTerminalValue().get()
                    else:
                        oids[idx-1]="None"
            oids = oids[-R:]
            vals = vals[-R:]
            toids = copy.copy(oids)
            for oid in toids:
                if oid == 'None': 
                    oids.remove(oid)
            if not oids:
                break
            req['pdu'].values()[0]['request_id'] = \
                req['pdu'].values()[0]['request_id'] + 1
        return retdata


    def _perfreq(self, req, encoded_oids):
        """perform a get based on req and a list of encoded_oids"""
        rsp = eval('v' + self.version).GETRESPONSE()
        myreq = req.encode(community=self.community, encoded_oids=encoded_oids)
        (answer, src) = self.client.send_and_receive(myreq)    
        rsp.decode(answer)
        if req != rsp:
            raise 'Unmatched response: %s vs %s' % (str(req), str(rsp))
        #if rsp['error_status'] and rsp['error_status'] != 2:
        if rsp['error_status']:
            raise "SNMPError", 'SNMP error #' + str(rsp['error_status']) + ' for OID #' \
                  + str(rsp['error_index'])
        oids = map(lambda x: x[0], map(asn1.OBJECTID().decode, \
                                       rsp['encoded_oids']))
        vals = map(lambda x: x[0](), map(asn1.decode, rsp['encoded_vals']))
        return (oids, vals, rsp)


        

    


if __name__ == '__main__':
    s = SnmpSession('olympus', community='g04par!')
    #print "uptime =", s.get('.1.3.6.1.2.1.1.3.0').values()[0]
    #print "descr =", s.get('.1.3.6.1.2.1.1.1').values()[0]
    #print 'conrad mac = ', asmac(s.get('.1.3.6.1.2.1.2.2.1.6.2').values()[0])
    #r = s.getTable(['.1.3.6.1.2.1.1', '.1.3.6.1.2.1.2.2.1'])
    r = s.getTable(['.1.3.6.1.2.1.2.2.1.1',])
    #r = s.getTable(['.1.3.6.1.2.1.2.2.1.10',])
    #r = s.getTable(['.1.3.6.1.2.1.2.2.1.1', '.1.3.6.1.2.1.2.2.1.6',])
    #for i in range(4,12):
    #    r = s.getTable(['.1.3.6.1.2.1.2.2.1.'+str(i),])
    a = r.keys()
    a.sort()
    for k in a:
        print k + "-->" + str(r[k])
