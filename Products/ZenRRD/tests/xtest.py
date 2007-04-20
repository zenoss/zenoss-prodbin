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
from SimpleXMLRPCServer import SimpleXMLRPCServer
from SocketServer import TCPServer
TCPServer.allow_reuse_address = True
TCPServer.request_queue_size = 100

def load():
    return dict(zip('load1 load5 load10'.split(),
                    open('/proc/loadavg').read().split()))
def load2():
    return tuple(open('/proc/loadavg').read().split())

def cs():
    return int(open('/proc/stat').read().split('\n')[3].split()[1])

s = SimpleXMLRPCServer( ('', 1234) )
s.register_function(load, 'load')
s.register_function(load2, 'load2')
s.register_function(cs, 'cs')
s.serve_forever()

