#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""SnmpSessionTest

Tests for SnmpSession

$Id: SnmpSessionTest.py,v 1.3 2002/12/14 20:08:53 edahl Exp $"""

__version__ = "$Revision: 1.3 $"[11:-2]

import unittest

from Products.SnmpCollector.SnmpSession import SnmpSession

class SnmpSessionTest(unittest.TestCase):
    
    snmpDescrOid = '.1.3.6.1.2.1.1.1.0'
    snmpUpTimeOid = '.1.3.6.1.2.1.1.3.0'
    
    ipTableOid = '.1.3.6.1.2.1.4.20.1'
    ipMap = {'.1': 'ipAddress',
             '.2': 'ifIndex',
             '.3': 'netmask'}

    def setUp(self):
        self.sess = SnmpSession("dhcp160")
    
    def tearDown(self):
        self.sess = None 

    def testGetDescr(self):
        data = self.sess.get(self.snmpDescrOid)
        self.failUnless(data)

    def testGetTable(self):
        data = self.sess.getTable(self.ipTableOid)
        self.failUnless(data)
        #self.failUnless(data.has_key('.1.3.6.1.2.1.4.20.1.1.127.0.0.1'))

    def testGetBulkTable(self):
        data = self.sess.getBulkTable(self.ipTableOid)
        self.failUnless(data)


    def testCollectSnmpTable(self):
        data = self.sess.collectSnmpTable(self.ipTableOid)
        self.failUnless(data)
        for k in data.keys():
            self.failUnless(data[k]['.1'])

    def testSnmpTableMap(self):
        data = self.sess.collectSnmpTable(self.ipTableOid)
        self.failUnless(data)
        ks = data.keys()
        ip = data[ks[0]]['.1']
        netmask = data[ks[0]]['.3']
        maped = self.sess.snmpTableMap(data, self.ipMap)
        self.failUnless(ip == maped[0]['ipAddress'])
        self.failUnless(netmask == maped[0]['netmask'])
        print maped

    def testSnmpTableMapBulk(self):
        data = self.sess.collectSnmpTable(self.ipTableOid,bulk=1)
        self.failUnless(data)
        ks = data.keys()
        ip = data[ks[0]]['.1']
        netmask = data[ks[0]]['.3']
        maped = self.sess.snmpTableMap(data, self.ipMap)
        self.failUnless(ip == maped[0]['ipAddress'])
        self.failUnless(netmask == maped[0]['netmask'])
        print maped

    def testUpTime(self):
        data = self.sess.get(self.snmpUpTimeOid)
        self.failUnless(data[self.snmpUpTimeOid] > 0)

if __name__ == "__main__":
    unittest.main()
