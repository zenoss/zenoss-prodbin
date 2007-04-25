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
import xmlrpclib
from AuthTransport import BasicAuthTransport

username='edahl'
password='sine440'
pingconfsrv='http://localhost:8080/zport/dmd/Monitors/StatusMonitors/Default'

trans = BasicAuthTransport(username, password)
server = xmlrpclib.Server(pingconfsrv,transport=trans)
devices = server.getPingDevices()
for device in devices:
    print device


