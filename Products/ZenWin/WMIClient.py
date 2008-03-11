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

import socket
import win32com.client
import logging
log = logging.getLogger("zen.WMIClient.WMIClient")

locator = win32com.client.Dispatch("WbemScripting.SWbemLocator")
refresher = win32com.client.Dispatch("WbemScripting.SWbemRefresher")

def refresh(): 
    """Refresh all data connections.
    """
    refresher.refresh()

#class WMI(object):
class WMIClient(object):

    def __init__(self, device, datacollector=None, plugins=[]):
        self.host = device.id
        if socket.getfqdn().lower() == device.id.lower(): 
            self.host = "."
            device.zWinUser = device.zWinPassword = ""
        elif device.manageIp is not None:
            self.host = device.manageIp
        self.name = device.id
        self.user = device.zWinUser
        self.passwd = device.zWinPassword
        
        self.authority = ""
        self.namespace = "root\cimv2"
        self.locale = ""
        self.flags = 0
        self.valueset = None
        self.datacollector = datacollector
        self.plugins = plugins

        #self._getdata = {}
        #self._tabledata = {}
        
        self.results = []
        
    
    def connect(self):
        log.debug("connect to %s, user %s", self.host, self.user)
        self._wmi = locator.ConnectServer(self.host,
                                          self.namespace,
                                          self.user,
                                          self.passwd,
                                          self.locale,
                                          self.authority,
                                          self.flags,
                                          self.valueset)

    def close(self):
        if hasattr(self, '_wmi'):
            del self._wmi


    def query(self, queries):
        if not hasattr(self, '_wmi'): 
            raise ValueError("WMI connection is closed")
        #flags = wbemFlagReturnImmediately | wbemFlagForwardOnly
        flags = 0x10 | 0x20
        queryResult = {}
        for (tableName, query) in queries.items():
            query = query.replace ("\\", "\\\\")
            queryResult[tableName] = self._wmi.ExecQuery(query, iFlags=flags)
        return queryResult


    def run(self):
        self.connect()
        for plugin in self.plugins:
            pluginName = plugin.name()
            log.debug("Sending queries for plugin: %s", pluginName)
            log.debug("Queries: %s" % str(plugin.queries().values()))
            result = self.query(plugin.queries())
            self.results.append((plugin, result))
        self.close()
        
        
    def getResults(self):
        """Return data for this client
        """
        return self.results 
        

    def addEnum(self, classname):
        """Add a set of classname instances to the refresher
        can be polled later for latest info.
        """
        self._results[classname] = refresher.addEnum(self._wmi, classname)        

    def results(self, classname):
        """Return results of instances from classname that was added by addEnum.
        """
        return self._results.get(classname,[])
    

    def instance(self, classname):
        """Return a single instance of the class name passed.
        """
        return self.instances(classname)[0]


    def instances(self, classname):
        """Return all instances of a given class name.
        """
        if not hasattr(self, '_wmi'): 
            raise ValueError("WMI connection is closed")
        return self._wmi.InstancesOf(classname)


    def watcher(self, wql=None):
        """Return a watcher object that can be called
        to check for new events.
        "SELECT * from __InstanceCreationEvent WITHIN 1 where 
            TargetInstance ISA 'Win32_NTLogEvent'"
        """
        if not hasattr(self, '_wmi'): 
            raise ValueError("WMI connection is closed")
        if not wql:
            wql = """SELECT * from __InstanceCreationEvent WITHIN 1 where """\
                  """TargetInstance ISA 'Win32_NTLogEvent'"""
        log.debug(wql)
        return _watcher(self._wmi.ExecNotificationQuery(wql))


class _watcher(object):


    def __init__(self, event):
        self.event = event


    def nextEvent(self, timeout=0):
        """Poll for next event wait timeout for response return value.
        """
        return self.event.NextEvent(timeout).Properties_("TargetInstance").Value


