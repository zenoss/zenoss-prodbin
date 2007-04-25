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

from AuthTransport import BasicAuthTransport
import xmlrpclib

username = 'edahl'
password = 'sine440'
url = 'localhost:8080/RrdRenderServer'

trans = BasicAuthTransport(username, password)
server = xmlrpclib.Server(url,transport=trans)

i = server.render


