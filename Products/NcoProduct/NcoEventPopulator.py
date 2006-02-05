#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""NcoEventPopulator

Populate netcool events based on the data model.
Calls to getDeviceEventInfo on Confmon.DeviceClass
to get the data list to populate into the events.  Requires
Sybase libraries to interact with Omnibus database.

$Id: NcoEventPopulator.py,v 1.21 2003/05/16 21:00:32 edahl Exp $"""

__version__ = "$Revision: 1.21 $"[11:-2]

import socket
import time
import sys
import os.path
import logging
import xmlrpclib

import Globals

from Products.ZenUtils.Utils import basicAuthUrl
from Products.ZenUtils.ConfDaemon import ConfDaemon

from DbAccessBase import DbAccessBase

class NcoEventPopulator(ConfDaemon, DbAccessBase):

    def __init__(self):
        ConfDaemon.__init__(self) 
        self.backend = self.options.backend
        self.hostname = self.options.hostname
        self.omniname = self.options.omniname
        self.username = self.options.username
        self.password = self.options.password
        self.zurl = self.options.zopeurl
        self.zusername = self.options.zopeusername
        self.zpassword = self.options.zopepassword
        self.cycletime = int(self.options.cycletime)
        self.configCycleInterval = int(self.options.configcycle)

        self.configTime = 0
        self.deviceInfo = {} #[fqdn] -> (SystemName, Location, 
                              #          productionState, deviceClass) 
        self._v_db = None


    def getDeviceInfo(self):
        """getDeviceInfo() -> load device information from zope"""
        if time.time()-self.configTime > self.configCycleInterval*60:
            self.log.info('Reloading device informtion from server')
            url = basicAuthUrl(self.zusername, self.zpassword, self.zurl)
            server = xmlrpclib.Server(url)
            for i in range(3):
                try:
                    self.deviceInfo = server.getEventDeviceInfo()
                except socket.error:
                    self.log.critical("xmlrpc server %s not available" %
                                        self.zurl)
                    self.log.warn("failed to renew configuration information")
                except Exception, e:
                    self.log.exception("an unexpected exception was found")

                if self.deviceInfo:
                    self.configTime = time.time()
                    return
                else:
                    self.log.critical("no configuration found retry in 20 secs")
                    time.sleep(20) 
            sys.exit(1)


    def getNewEvents(self):
        """getNewEvents() -> get unprocessed events from netcool"""
        select = "select Node, ServerSerial, ServerName from status "
        select += "where ps_id = 0;"
        data = []
        curs = self._getCursor()
        curs.execute(select)
        data = curs.fetchall()
        self._closeDb()
        return data


    def updateEvent(self, curs, serverSerial, serverName, 
                    systemName=None, location=None, 
                    productionState=-10, deviceClass=None):
        """updateEvent(event) -> update event info in unprocessed event"""

        update = "update status set "
        if systemName: update += " System = '" + systemName + "', "
        if location: update += " Location = '" + location + "', "
        if deviceClass: update += " DeviceClass = '" + deviceClass + "', "
        update += " ps_id = " + str(productionState) 
        update += " where ServerSerial = " + str(serverSerial) + " and "
        update += " ServerName = '" + serverName + "';"
        #print update
        curs.execute(update)


    def processEvents(self):
        """processEvent() -> run through one event processing cycle"""
        try:
            events = self.getNewEvents()
            curs = self._getCursor()
            for event in events:
                node, serverSerial, serverName = event
                node = self._cleanstring(node)
                serverName = self._cleanstring(serverName)
                if self.deviceInfo.has_key(node):
                    self.log.info("Node %s found in device info" % node)
                    (systemName, location, 
                    productionState, deviceClass) = self.deviceInfo[node]
                    self.updateEvent(curs, serverSerial, serverName, systemName,
                                    location, productionState, deviceClass)
                else:
                    self.updateEvent(curs, serverSerial, serverName)
                    self.log.warn("Node %s not found in device info" % node)
            self._closeDb() 
        except:
            self.log.exception("Problem processing events")


    def mainLoop(self):
        """mainLoop() -> entry point to begin operations"""
        if self.cycletime:
            while 1:
                startLoop = time.time()
                self.log.info("Starting event processing loop")
                self.getDeviceInfo()
                self.processEvents()
                runTime = time.time()-startLoop
                self.log.info("Ending event processing loop")
                self.log.info("Loop runtime = %s seconds" % runTime)
                if runTime < self.cycletime:
                    time.sleep(self.cycletime - runTime)
        else:
            self.log.info("Starting single processing run")
            self.getDeviceInfo()
            self.processEvents()
            self.log.info("Ending single processing run")


    def buildOptions(self):
        ConfDaemon.buildOptions(self)
        self.parser.add_option("-o", "--omniname", action="store", 
                        type="string", dest="omniname",
                        help="name of omnibus database")
        
        self.parser.add_option("-u", "--omniusername", action="store", 
                        type="string", dest="omniusername",
                        help="username for omnibus database")

        self.parser.add_option("-p", "--omnipassword", action="store", 
                        type="string", dest="omnipassword",
                        help="password for omnibus database")

        self.parser.add_option("-z", "--zurl", action="store", 
                        type="string", dest="zurl",
                        help="url for zope server device class")

        self.parser.add_option("-U", "--zusername", action="store", 
                        type="string", dest="zusername",
                        help="username for zope server")

        self.parser.add_option("-P", "--zpassword", action="store", 
                        type="string", dest="zpassword",
                        help="password for zope server")
        
        self.parser.add_option("-y", "--cycletime", action="store", 
                        type='int', dest="cycletime", default=7,
                        help="population cycle time in seconds")
        
        self.parser.add_option("-i", "--configcycle", action="store", 
                        type='int', dest="configcycle", default=20,
                        help="device reload cycle time in minutes default=20")


if __name__ == '__main__':
    ncoevpop = NcoEventPopulator()
    ncoevpop.mainLoop() 
