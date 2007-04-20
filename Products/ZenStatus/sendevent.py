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
import xmlrpclib
from AuthTransport import BasicAuthTransport

trans = BasicAuthTransport('edahl', 'edahl')
server = xmlrpclib.Server('http://emi0:8080/cvportal/netcool', transport=trans)
e = {}
e['Node'] = 'conrad.confmon.loc'
e['Summary'] = 'this is a test message'
e['Class'] = 100
e['Agent'] = 'PingProbe'
e['Severity'] = 4
e['Type'] = 2
e['AlertGroup'] = 'Ping'
e['NodeAlias'] = '1.2.3.4'

server.sendEvent(e)

