# recipe for doing basic authentication xml rpc calls in twisted
import base64
import xmlrpclib

from twisted.web import xmlrpc
from twisted.internet import reactor, defer

class AuthQueryProtocol(xmlrpc.QueryProtocol):
    '''
    We're just over-riding the connectionMade() method so that we
    can add the Authorization header.
    '''
    def connectionMade(self):
        self.sendCommand('POST', self.factory.url)
        self.sendHeader('User-Agent', 'Twisted/XMLRPClib')
        self.sendHeader('Host', self.factory.host)
        self.sendHeader('Content-type', 'text/xml')
        self.sendHeader('Content-length', 
            str(len(self.factory.payload)))
        if self.factory.user:
            auth = base64.encodestring('%s:%s' % (
                self.factory.user, self.factory.password))
            self.sendHeader('Authorization', 'Basic %s' % auth)
        self.endHeaders()
        self.transport.write(self.factory.payload)

payloadTemplate = xmlrpc.payloadTemplate.replace('?>',
                                                 ' encoding="iso8859-1"?>')
class AuthQueryFactory(xmlrpc.QueryFactory):
    '''
    We're using a Uri object here for the url, diverging pretty
    strongly from how it's done in t.w.xmlrpc. This is done for 
    convenience and simplicity of presentation in this recipe.
    '''
    deferred = None
    protocol = AuthQueryProtocol

    def __init__(self, url, username, password, method, *args):
        self.url, self.host, self.user, self.password = (
            url.path, url.host, username, password)
        if url.port:
            self.host = '%s:%d' % (url.host, url.port)
        self.payload = payloadTemplate % (
            method, xmlrpclib.dumps(args))
        self.deferred = defer.Deferred()

def _splitGrab(full, div):
    parts = full.split(div, 1)
    if len(parts) > 1:
        return parts
    return parts[0], None

class Uri:
    def __init__(self, url):
        parts = url.split('/')
        self.path = '/' + '/'.join(parts[3:])
        self.host = parts[2]
        self.user, self.host = _splitGrab(self.host, '@')
        if not self.host:
            self.user, self.host = '', self.user
        self.user, self.password = _splitGrab(self.user, ':')
        self.host, self.port = _splitGrab(self.host, ':')
        if self.port:
            self.port = int(self.port)
        self.scheme, unused = _splitGrab(parts[0], ':')

class AuthProxy:
    '''
    A Proxy for making remote XML-RPC calls that supports Basic
    Authentication. There's no sense subclassing this, since it needs
    to override all of xmlrpc.Proxy.

    Pass the URL of the remote XML-RPC server to the constructor.

    Use proxy.callRemote('foobar', *args) to call remote method
    'foobar' with *args.
    '''
    def __init__(self, url, username, password):
        self.url = Uri(url)
        self.host = self.url.host
        self.port = self.url.port
        self.username = username
        self.password = password
        self.secure = self.url.scheme == 'https'

    def callRemote(self, method, *args):
        factory = AuthQueryFactory(self.url, self.username, self.password,
                                   method, *args)
        if self.secure:
            from twisted.internet import ssl
            reactor.connectSSL(self.host, self.port or 443,
                               factory, ssl.ClientContextFactory())
        else:
            reactor.connectTCP(self.host, self.port or 80, factory)
        return factory.deferred

