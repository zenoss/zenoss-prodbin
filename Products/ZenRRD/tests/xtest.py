from SimpleXMLRPCServer import SimpleXMLRPCServer
from SocketServer import TCPServer
TCPServer.allow_reuse_address = True
TCPServer.request_queue_size = 100

def load():
    return dict(zip('load5 load10 load15'.split(),
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
