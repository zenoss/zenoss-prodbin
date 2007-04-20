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
# This program is part of Zenoss Core, an open source monitoring platform.
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
# For complete information please visit: http://www.zenoss.com/oss/

from xmlrpclib import ServerProxy
from socket import getfqdn

from zenhub import XML_RPC_PORT

def main():
    proxy = ServerProxy('http://zenoss:zenoss@localhost:%d' % XML_RPC_PORT)
    proxy.sendEvent(dict(summary='This is an event',
                         device=getfqdn(),
                         Class='/Status/Ping',
                         component='test',
                         severity=5))
    print proxy.getDevicePingIssues()

main()

