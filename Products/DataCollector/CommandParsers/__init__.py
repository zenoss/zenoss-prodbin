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
from Uname_A import Uname_A
from Unix_df_k import Unix_df_k

from Linux_netstat_an import Linux_netstat_an
from Linux_netstat_rn import Linux_netstat_rn
from Linux_ifconfig import Linux_ifconfig

from CiscoDhcpHelperAddress import CiscoDhcpHelperAddress
from CiscoShowHardware import CiscoShowHardware

def initCommandParsers(dataCollector):
    dataCollector.addCommandParser(Uname_A)
    dataCollector.addCommandParser(Unix_df_k)

    dataCollector.addCommandParser(Linux_netstat_an)
    dataCollector.addCommandParser(Linux_netstat_rn)
    dataCollector.addCommandParser(Linux_ifconfig)

    dataCollector.addCommandParser(CiscoDhcpHelperAddress)
    dataCollector.addCommandParser(CiscoShowHardware)

