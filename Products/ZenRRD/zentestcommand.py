##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__=''' ZenTestCommand

Test the run of a ZenCommand and print output

$Id$'''

__version__ = "$Revision$"[11:-2]

import os
import popen2
import fcntl
import time
import sys
import select
import logging
import signal
from copy import copy
log = logging.getLogger("zen.zentestcommand")

import Globals
from Products.ZenUtils.ZenScriptBase import ZenScriptBase

snmptemplate = ("snmpwalk -c%(zSnmpCommunity)s "
                "-%(zSnmpVer)s %(manageIp)s %(oid)s")


class TestRunner(ZenScriptBase):

    def __init__(self):
        ZenScriptBase.__init__(self, connect=True)
        self.getDataRoot()

    def getCommand(self, devName=None, dsName=None):
        if not devName: devName = self.options.devName
        if not dsName: dsName = self.options.dsName
        devices = self.dmd.getDmdRoot("Devices")
        device = devices.findDevice(devName)
        if not device:
            self.write('Could not find device %s.' % devName)
            sys.exit(1)
        dataSource = None
        for templ in device.getRRDTemplates():
            for ds in templ.getRRDDataSources():
                if ds.id==dsName: 
                    dataSource = ds
                    break
                if dataSource: break
        if not dataSource:
            self.write('No datasource %s applies to device %s.' % (dsName,
                                                                   devName))
            sys.exit(1)
        if dataSource.sourcetype=='COMMAND':
            return dataSource.getCommand(device)
        elif dataSource.sourcetype=='SNMP':
            snmpinfo = copy(device.getSnmpConnInfo().__dict__)
            snmpinfo['oid'] = dataSource.getDescription()
            return snmptemplate % snmpinfo
        else:
            self.write('No COMMAND or SNMP datasource %s applies to device %s.' % (
                                                            dsName, devName))

    def execute(self, cmd):
        child = popen2.Popen4(cmd)
        flags = fcntl.fcntl(child.fromchild, fcntl.F_GETFL)
        fcntl.fcntl(child.fromchild, fcntl.F_SETFL, flags | os.O_NDELAY)
        pollPeriod = 1
        timeout = max(self.options.timeout, 1)
        endtime = time.time() + timeout
        firstPass = True
        while time.time() < endtime and (
            firstPass or child.poll()==-1):
            firstPass = False
            r,w,e = select.select([child.fromchild],[],[],pollPeriod)
            if r:
                t = child.fromchild.read()
                if t:
                    self.write(t)
        if child.poll()==-1:
            self.write('Command timed out')
            os.kill(child.pid, signal.SIGKILL)

    def write(self, text):
        print text

    def run(self):
        device, dsName = self.options.device, self.options.dsName
        if not (device and dsName):
            self.write("Must provide a device and datasource.")
            sys.exit(2)
        d = self.getCommand(device, dsName)
        self.execute(d)

    def buildOptions(self):
        ZenScriptBase.buildOptions(self)
        self.parser.add_option('-d', '--device',
                    dest="device",
                    help="Device on which to test command")
        self.parser.add_option('--datasource',
                    dest="dsName",
                    help="COMMAND datasource to test")
        self.parser.add_option('-t', '--timeout',
                    dest="timeout", default=1, type="int",
                    help="Command timeout")


if __name__=='__main__':
    tr = TestRunner()
    tr.run()
