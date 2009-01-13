###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import traceback
from xmlrpclib import ServerProxy, ProtocolError
from Products.ZenTestCase.BaseTestCase import BaseTestCase

class TestXmlRpc(BaseTestCase):
    """Test XML-RPC services used in the Dev Guide against our Zenoss server"""

    # Args for some of these functions are found at 
    # xml:id="dev_mgmt_xml_rpc_attributes"
    # in the Dev Guide

    def setUp(self):
        self.baseUrl = 'http://admin:zenoss@localhost:8080/zport/dmd/'
        self.anonUrl = 'http://localhost:8080/zport/dmd/'
        self.device = 'xmlrpc_testdevice'


    def testGetMethods(self):
        """Verify that the basic system XML-RPC introspection functions work
           system.listMethods()
           system.methodSignature(func)
           system.methodHelp(func)

           Zenoss doesn't currently support XML-RPC introspection methods
        """
        return
        try:
            serv = ServerProxy( self.baseUrl ) 
            methods = serv.system.listMethods()
        except:
            msg= traceback.format_exc(limit=0)
            self.fail( msg )

        self.assert_( len(methods) > 0 )
        from random import choice
        sample_func = choice(methods)
        try:
            serv.system.methodSignature(sample_func)
            serv.system.methodHelp(sample_func)
        except:
            msg= "Random function= '%s' %s" % (sample_func, traceback.format_exc(limit=0))
            self.fail( msg )


    def testGetEvents(self):
        "Look for events in the Event Console using XML-RPC"
        try:
            serv = ServerProxy( self.baseUrl + 'ZenEventManager' ) 
            serv.getEventList()
        except:
            msg= traceback.format_exc(limit=0)
            self.fail( msg )

        # NB: it's possible that we don't have any events yet


    def testCreateEvent(self):
        "Create an event using XML-RPC"
        serv = ServerProxy( self.baseUrl + 'ZenEventManager' ) 
        evt = {
          'device':self.device,
          'component':'eth0', 
          'summary':'eth0 is down',
          'severity':4,
          'eventClass':'/Net'
        } 

        try:
            serv.sendEvent(evt) 
            post_events = serv.getEventList( { 'device':self.device, } )
        except:
            msg= traceback.format_exc(limit=0)
            self.fail( msg )

        self.assert_( len(post_events) >= 1 )


    def testClearEvent(self):
        "Clear an event using XML-RPC"
        serv = ServerProxy( self.baseUrl + 'ZenEventManager' )
        evt = {
          'device':self.device,
          'component':'eth0',
          'summary':'eth0 is down',
          'severity':4,
          'eventClass':'/Net'
        }

        # Now add an event to ensure that we have something
        # to delete
        try:
            serv.sendEvent(evt)
            events = serv.getEventList( { 'device':self.device, } )
        except:
            msg= traceback.format_exc(limit=0)
            self.fail( msg )

        self.assert_( len(events) >= 1 )

        # Gather our event ids and delete them
        evids= [ ev['evid'] for ev in events ]
        try:
            serv.manage_deleteEvents(evids)
            events = serv.getEventList( { 'device':self.device, } )
        except:
            msg= traceback.format_exc(limit=0)
            self.fail( msg )

        self.assertEquals( len(events), 0 )


    def testAddDevice(self):
        "Add a remote device through XML-RPC"
        return
        from random import randrange
        randobox= "%s%d" % ( self.device, randrange(1,100) )

        devpath= '/Server/Linux'
        dev = {
          'deviceName':randobox,
          'devicePath':devpath,
          'discoverProto':'none',
          'manageIp':'192.168.10.177',
        }

        randobox= 'cent5c'
        try:
            serv = ServerProxy( self.baseUrl )
            serv.DeviceLoader.loadDevice(randobox,devpath)
            #serv.DeviceLoader.loadDevice(dev)
        except:
            msg= "URL='%s'\n%s" % (self.baseUrl, traceback.format_exc(limit=0) )
            self.fail( msg )

        # We were able to create it.  How about to get info from it?
        #randobox= "test-cent4-64-1.zenoss.loc"
        #url= "%sDevices%s/devices/%s" % ( self.baseUrl, devpath, randobox )
        #try:
        #    id = serv.getManageIp()
        #except:
        #    msg= "URL='%s'\n%s" % (url, traceback.format_exc(limit=0) )
        #    self.fail( msg )


    def testAddEditDevice(self):
        "Add and edit a remote device through XML-RPC"
        return
        from random import randrange
        randobox= "%s%d" % ( self.device, randrange(101,200) )

        devpath= '/Server/Linux'
        dev = {
          'deviceName':randobox,
          'devicePath':devpath,
          'discoverProto':'none',
        }

        url = self.baseUrl + 'DeviceLoader'
        try:
            serv = ServerProxy( url )
            serv.loadDevice(dev)
        except:
            msg= "URL='%s'\n%s" % (url, traceback.format_exc(limit=0) )
            self.fail( msg )

        randobox= "test-cent4-64-1.zenoss.loc"
        url= "%sDevices%s/devices/%s" % ( self.baseUrl, devpath, randobox )
        try:
            serv = ServerProxy( url )
            serv.manage_editDevice('MYTAG', 'MYSERIALNUM')
        except:
            msg= "URL='%s'\n%s" % (url, traceback.format_exc(limit=0) )
            self.fail( msg )


    def testAddDeleteDevice(self):
        "Add then delete a remote device through XML-RPC"
        # Note: This does too much in one test, but we're a
        #       little hampered by not being able to verify
        #       if the device got created.
        return
        url = self.baseUrl + 'DeviceLoader'
        devpath= '/Server/Linux'

        dev = {
          'deviceName':self.device,
          'devicePath':devpath,
          'discoverProto':'none',
        } 

        try:
            serv = ServerProxy( url )
            serv.DeviceLoader.loadDevice(dev)
        except:
            msg= "URL='%s'\n%s" % (url, traceback.format_exc(limit=0) )
            self.fail( msg )

        # Try obtaining this new device
        url= "%sDevices%s/devices/%s" % ( self.baseUrl, devpath, self.device )
        try:
            serv = ServerProxy( url )
            id = serv.getManageIp()
#serv.manage_editDevice('MYTAG', 'MYSERIALNUM')
            print "ip= %s" % id
        except:
            msg= "URL='%s'\n%s" % (url, traceback.format_exc(limit=0) )
            self.fail( msg )

#deleteDevice


    def testAnonPrivs(self):
        "Ensure that unauthenticated users don't have access to sensitive info"
        url = self.anonUrl # 'http://localhost:8080/zport/dmd/'

        # Set up anonymous unauthenticated connection
        try:
            serv = ServerProxy( url )
        except:
            msg= "URL='%s'\n%s" % (url, traceback.format_exc(limit=0) )
            self.fail( msg )

        # Access database info
        for prop in [ "username", "password", "host", "database" ]:
            self.assertRaises( ProtocolError, serv.ZenEventManager.getProperty, prop)

        # Access user info
        self.assertRaises( ProtocolError, serv.ZenUsers.getAllUserSettingsNames )
        self.assertRaises( ProtocolError, serv.ZenUsers.admin.getUserRoles )

        # Access device connection info
        self.assertRaises( ProtocolError, serv.Devices.Server.Windows.getProperty, "zWinUser")
        self.assertRaises( ProtocolError, serv.Devices.Server.Windows.getProperty, "zWinPassword")


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestXmlRpc))
    return suite
