
from xmlrpclib import ServerProxy
from socket import getfqdn

from zenhub import XML_RPC_PORT

def main():
    proxy = ServerProxy('http://localhost:%d' % XML_RPC_PORT)
    proxy.sendEvent(dict(summary='This is an event',
                         device=getfqdn(),
                         Class='/Status/Ping',
                         component='test',
                         severity=5))
    print proxy.getDevicePingIssues()

main()
