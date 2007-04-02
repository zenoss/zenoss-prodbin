
from xmlrpclib import ServerProxy
from socket import getfqdn

from zenhub import XML_RPC_PORT

def main():
    proxy = ServerProxy('http://localhost:%d' % XML_RPC_PORT)
    proxy.sendEvent(summary='This is an event',
                    device=getfqdn(),
                    component='test',
                    severity=5)
    print proxy.getDevicePingIssues()
