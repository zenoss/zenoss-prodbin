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

import pythoncom
import pywintypes
import threading
from wmiclient import WMI
import logging
log = logging.getLogger("zen.StatusTest")

class StatusTest(WMI):
    """track the results of a status test"""
    def __init__(self, zem, name, user, passwd, svcs, debug=False):
        WMI.__init__(self, name, user, passwd)
        self.zem = zem
        self.svcs = svcs
        self.lastpoll = {}
        self.debug = debug
        self._plugins = []
        self._wmi = None
        self.failed = False
        self._done = False
        self._thread = None
  

    def sendFail(self, msg="", evtclass="/Status/Wmi"):
        evt = { 'eventClass':evtclass, 'agent': 'zenwin', 'severity':3 }
        if not msg:
            msg = "wmi connection failed %s" % self.name
        evt['component'] = ""
        evt['summary'] = msg
        evt['device'] = self.name
        self.zem.sendEvent(evt)
        log.warn("%s %s" % (self.name, msg))
        #log.exception(msg)
        self.failed = True

    def setPlugins(self, plugins):
        self._plugins = plugins


    def start(self):
        self._thread = threading.Thread(target=self.run)
        self._thread.start()


    def run(self):
        try:
	    if not self.debug: pythoncom.CoInitialize()
            try:
                self.failed = False
                log.debug("device:%s user:%s", self.name, self.user)
                self.connect()
                self.runplugins()
            except (SystemExit, KeyboardInterrupt): raise
            except pywintypes.com_error, e:
                msg = "wmi connection failed: "
                code,name,info,param = e
                wmsg = "%s: %s" % (abs(code), name)
                if info:
                    wcode, source, descr, hfile, hcont, scode = info
                    if descr: wmsg = descr.strip()
                msg += wmsg
                self.sendFail(msg, evtclass="/Status/Wmi/Conn")
            except:
                self.sendFail()
        finally:
            self.close()
	    if not self.debug: pythoncom.CoUninitialize()


    def runplugins(self):
        for plugin in self._plugins:
            try:
                plugin.run(self, self.zem)
            except (SystemExit, KeyboardInterrupt): raise
            except pywintypes.com_error, e:
                msg = "plugin %s failed on %s msg:" %(plugin.name,self.name)
                code,name,info,param = e
                wmsg = "%s: %s" % (abs(code), name)
                if info:
                    wcode, source, descr, hfile, hcont, scode = info
                    if descr: wmsg = descr.strip()
                msg += wmsg
                self.sendFail(msg)
            except:
                msg = "plugin %s failed on %s" % (plugin.name,self.name)
                self.sendFail(msg)


    def done(self):
        return not self._thread.isAlive()
