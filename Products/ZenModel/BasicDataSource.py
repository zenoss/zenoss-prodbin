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

__doc__="""BasicDataSource

Defines attributes for how a datasource will be graphed
and builds the nessesary DEF and CDEF statements for it.
"""

from Products.ZenModel import RRDDataSource
from AccessControl import ClassSecurityInfo, Permissions
from Globals import InitializeClass
from Products.ZenEvents.ZenEventClasses import Cmd_Fail
from Products.ZenUtils.Utils import executeStreamCommand
from Products.ZenWidgets import messaging
from copy import copy
import cgi, time

snmptemplate = ("snmpwalk -c%(zSnmpCommunity)s "
                "-%(zSnmpVer)s %(manageIp)s %(oid)s")

def checkOid(oid):
    import string
    for c in string.whitespace:
        oid = oid.replace(c, '')
    oid = oid.strip('.')
    numbers = oid.split('.')
    map(int, numbers)
    if len(numbers) < 3:
        raise ValueError("OID too short")
    return oid


class BasicDataSource(RRDDataSource.SimpleRRDDataSource):

    __pychecker__='no-override'

    sourcetypes = ('SNMP', 'COMMAND')
    
    sourcetype = 'SNMP'
    eventClass = Cmd_Fail
    oid = ''
    parser = "Auto"

    usessh = False

    _properties = RRDDataSource.RRDDataSource._properties + (
        {'id':'oid', 'type':'string', 'mode':'w'},
        {'id':'usessh', 'type':'boolean', 'mode':'w'},
        {'id':'parser', 'type':'string', 'mode':'w'},
        )

    _relations = RRDDataSource.RRDDataSource._relations + (
        )
    
    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
    { 
        'immediate_view' : 'editBasicDataSource',
        'actions'        :
        ( 
            { 'id'            : 'edit'
            , 'name'          : 'Data Source'
            , 'action'        : 'editBasicDataSource'
            , 'permissions'   : ( Permissions.view, )
            },
        )
    },
    )

    security = ClassSecurityInfo()

    def addDataPoints(self):
        """
        Overrides method defined in SimpleRRDDataSource. Only sync the
        datapoint with the datasource if the datasource type is SNMP.
        """
        if self.sourcetype == 'SNMP':
            RRDDataSource.SimpleRRDDataSource.addDataPoints(self)

    def getDescription(self):
        if self.sourcetype == "SNMP":
            return self.oid
        if self.sourcetype == "COMMAND":
            if self.usessh:
                return self.commandTemplate + " over SSH"
            else:
                return self.commandTemplate
        return RRDDataSource.RRDDataSource.getDescription(self)


    def useZenCommand(self):
        if self.sourcetype == 'COMMAND':
            return True
        return False


    def zmanage_editProperties(self, REQUEST=None):
        'add some validation'
        if REQUEST:
            oid = REQUEST.get('oid', '')
            if oid:
                try:
                    REQUEST.form['oid'] = checkOid(oid)
                except ValueError:
                    messaging.IMessageSender(self).sendToBrowser(
                        'Invalid OID',
                        "%s is an invalid OID." % oid,
                        priority=messaging.WARNING
                    )
                    return self.callZenScreen(REQUEST)

        return RRDDataSource.SimpleRRDDataSource.zmanage_editProperties(
                                                                self, REQUEST)

    security.declareProtected('Change Device', 'manage_testDataSource')
    def manage_testDataSource(self, testDevice, REQUEST):
        ''' Test the datasource by executing the command and outputting the
        non-quiet results.
        '''
        out = REQUEST.RESPONSE

        def write(lines):
            ''' Output (maybe partial) result text.
            '''
            # Looks like firefox renders progressive output more smoothly
            # if each line is stuck into a table row.  
            startLine = '<tr><td class="tablevalues">'
            endLine = '</td></tr>\n'
            if out:
                if not isinstance(lines, list):
                    lines = [lines]
                for l in lines:
                    if not isinstance(l, str):
                        l = str(l)
                    l = l.strip()
                    l = cgi.escape(l)
                    l = l.replace('\n', endLine + startLine)
                    out.write(startLine + l + endLine)

        # Determine which device to execute against
        device = None
        if testDevice:
            # Try to get specified device
            device = self.findDevice(testDevice)
            if not device:
                messaging.IMessageSender(self).sendToBrowser(
                    'No device found',
                    'Cannot find device matching %s.' % testDevice,
                    priority=messaging.WARNING
                )
                return self.callZenScreen(REQUEST)
        elif hasattr(self, 'device'):
            # ds defined on a device, use that device
            device = self.device()
        elif hasattr(self, 'getSubDevicesGen'):
            # ds defined on a device class, use any device from the class
            try:
                device = self.getSubDevicesGen().next()
            except StopIteration:
                # No devices in this class, bail out
                pass
        if not device:
            messaging.IMessageSender(self).sendToBrowser(
                'No Testable Device',
                'Cannot determine a device against which to test.',
                priority=messaging.WARNING
            )
            return self.callZenScreen(REQUEST)

        # Get the command to run
        command = None
        if self.sourcetype=='COMMAND':
            command = self.getCommand(device)
        elif self.sourcetype=='SNMP':
            snmpinfo = copy(device.getSnmpConnInfo().__dict__)
            snmpinfo['oid'] = self.getDescription()
            command = snmptemplate % snmpinfo
        else:
            messaging.IMessageSender(self).sendToBrowser(
                'Test Failed',
                'Unable to test %s datasources' % self.sourcetype,
                priority=messaging.WARNING
            )
            return self.callZenScreen(REQUEST)
        if not command:
            messaging.IMessageSender(self).sendToBrowser(
                'Test Failed',
                'Unable to create test command.',
                priority=messaging.WARNING
            )
            return self.callZenScreen(REQUEST)

        # Render
        header, footer = self.commandTestOutput().split('OUTPUT_TOKEN')
        out.write(str(header))

        write("Executing command\n%s\n   against %s" % (command, device.id))
        write('')
        start = time.time()
        try:
            executeStreamCommand(command, write)
        except:
            import sys
            write('exception while executing command')
            write('type: %s  value: %s' % tuple(sys.exc_info()[:2]))
        write('')
        write('')
        write('DONE in %s seconds' % long(time.time() - start))
        out.write(str(footer))

    def parsers(self):
        from Products.ZenRRD.CommandParser import getParserNames
        return getParserNames(self.getDmd())



InitializeClass(BasicDataSource)
