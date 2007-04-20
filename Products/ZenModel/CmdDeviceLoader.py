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
#   Copyright (c) 2004 Zentinel Systems. 


__doc__="""cmdDeviceLoader.py

load devices from the command line by parsing a text file.

$Id: CmdDeviceLoader.py,v 1.1 2004/03/26 23:59:52 edahl Exp $"""

__version__ = "$Revision: 1.1 $"[11:-2]

from BasicDeviceLoader import BasicDeviceLoader
from Products.ZenUtils.BasicLoader import BasicLoader

class cmdDeviceLoader(BasicLoader, BasicDeviceLoader):

    def __init__(self):
        BasicLoader.__init__(self)
        BasicDeviceLoader.__init__(self, self.dataroot)

    
    def loaderBody(self,line):
        """loader body override to customize what will load"""
        fqdn = line
        self.log.info("Processing machine %s -- line %i" % 
                        (fqdn,self.lineNumber))
        dev = self.getDevice(fqdn)
        self.getDeviceInterfaces(dev)
        if self.options.system:
            sys = self.getSystem(self.options.system)
            dev.addRelation('system', sys)
        self.getPerformanceMonitor(self.options.perfServer, dev)
        self.getStatusMonitor(self.options.statusMonitor, dev)


    def buildOptions(self):
        BasicLoader.buildOptions(self)

        self.parser.add_option('--devicePath',
                    dest='devicePath',
                    default=None,
                    help='default device path for devices being loaded')

        self.parser.add_option('-N', '--noclassifier',
                    dest='useClassifier',
                    action="store_false",
                    default=1,
                    help='turn off the classifier during load')

        self.parser.add_option('--systemPath',
                    dest='systemPath',
                    default=None,
                    help='System Path to device /Mail/MTA')

        self.parser.add_option('--perfServer',
                    dest='perfServer',
                    default='',
                    help='Performance data collector with which to link Dmd devices')

        self.parser.add_option('--status',
                    dest='statusMonitor',
                    default='Default',
                    help='Status Monitor with which to link Dmd devices')
        
        self.parser.add_option('-c', '--snmpCommunity',
                    dest='snmpCommunity',
                    default='public',
                    help='SNMP community string')

        self.parser.add_option('-P', '--snmpPort',
                    dest='snmpPort',
                    default=161,
                    type='int',
                    help='SNMP port')

        self.parser.add_option('--manufacturer',
                    dest='manufacturer',
                    default='',
                    help='manufacturer of the device')

        self.parser.add_option('--model',
                    dest='model',
                    default='',
                    help='model of the device')

        self.parser.add_option('--groupPath',
                    dest='groupPath',
                    default='',
                    help='groupPath of the device')


if __name__ == "__main__":
    loader = BasicDeviceLoader()
    loader.loadDatabase()
    print "Database Load is finished!"
