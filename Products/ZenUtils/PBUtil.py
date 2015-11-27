##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


# taken from r1.10 of buildbot.sf.net/buildbot/pbutil.py

# flumotion has nearly the same code

__doc__ = """PBUtil
Base classes handy for use with PB clients.
"""

import logging
zenlog = logging.getLogger("zen.pbclientfactory")

from twisted.spread import pb

from twisted.spread.pb import PBClientFactory
from twisted.internet import protocol, reactor, defer, task
from twisted.internet.error import ConnectionClosed
import socket

OPTION_STATE = 1
CONNECT_TIMEOUT = 60

class ReconnectingPBClientFactory(PBClientFactory,
                                  protocol.ReconnectingClientFactory):
    """Reconnecting client factory for PB brokers.

    Like PBClientFactory, but if the connection fails or is lost, the factory
    will attempt to reconnect.

    Instead of using f.getRootObject (which gives a Deferred that can only
    be fired once), override the gotRootObject method.

    Instead of using the newcred f.login (which is also one-shot), call
    f.startLogin() with the credentials and client, and override the
    gotPerspective method.

    Instead of using the oldcred f.getPerspective (also one-shot), call
    f.startGettingPerspective() with the same arguments, and override
    gotPerspective.

    gotRootObject and gotPerspective will be called each time the object is
    received (once per successful connection attempt). You will probably want
    to use obj.notifyOnDisconnect to find out when the connection is lost.

    If an authorization error occurs, failedToGetPerspective() will be
    invoked.

    To use me, subclass, then hand an instance to a connector (like
    TCPClient).
    """
    __pychecker__='no-override'

    # maxDelay(secs) set to 5 minute maximum delay before attempting to
    # reconnect
    maxDelay = 300

    def __init__(self, connectTimeout=30, pingPerspective=True, pingInterval=30, pingtimeout=120):
        PBClientFactory.__init__(self)
        self._doingLogin = False
        self._doingGetPerspective = False
        self._scheduledConnectTimeout = None
        self._connectTimeout = connectTimeout
        # should the perspective be pinged. Perspective must have a ping method.
        self._shouldPingPerspective = pingPerspective
        # how often to ping
        self._pingInterval = pingInterval
        # how long to wait for a ping before closing connection
        self._pingTimeoutTime = pingtimeout
        # ref to the scheduled ping timeout call
        self._pingTimeout = None
        # looping call doing the ping
        self._pingCheck = None

        self._perspective = None

    def connectTCP(self, host, port):
        factory = self
        self.connector = reactor.connectTCP(host, port, factory)
        self.setKeepAlive(self.connector)
        return self.connector

    def setKeepAlive(self, connector):
        connector.transport.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, OPTION_STATE)
        connector.transport.socket.setsockopt(socket.SOL_TCP, socket.TCP_KEEPIDLE, CONNECT_TIMEOUT)
        interval = max(CONNECT_TIMEOUT / 4, 10)
        connector.transport.socket.setsockopt(socket.SOL_TCP, socket.TCP_KEEPINTVL, interval)
        connector.transport.socket.setsockopt(socket.SOL_TCP, socket.TCP_KEEPCNT, 2)

    def clientConnectionFailed(self, connector, reason):
        zenlog.debug("Failed to create connection to %s:%s - %s",
                     connector.host, connector.port, reason)
        self._perspective = None
        self._cancelConnectTimeout()
        PBClientFactory.clientConnectionFailed(self, connector, reason)
        # Twisted-1.3 erroneously abandons the connection on non-UserErrors.
        # To avoid this bug, don't upcall, and implement the correct version
        # of the method here.
        if self.continueTrying:
            self.connector = connector
            self.retry()

    def clientConnectionLost(self, connector, reason, reconnecting=1):
        zenlog.debug("Lost connection to %s:%s - %s", connector.host,
                     connector.port, reason.getErrorMessage())
        self._perspective = None
        self._cancelConnectTimeout()
        PBClientFactory.clientConnectionLost(self, connector, reason,
                                             reconnecting=reconnecting)
        RCF = protocol.ReconnectingClientFactory
        RCF.clientConnectionLost(self, connector, reason)

    def clientConnectionMade(self, broker):
        zenlog.debug("Connected")
        self._cancelConnectTimeout()
        self.resetDelay()
        PBClientFactory.clientConnectionMade(self, broker)
        if self._doingLogin:
            self._startConnectTimeout("Login")
            self.doLogin(self._root)
        if self._doingGetPerspective:
            self.doGetPerspective(self._root)
        self.gotRootObject(self._root)

    def startedConnecting(self, connector):
        zenlog.debug("Starting connection...")
        self._startConnectTimeout("Initial connect")
        self.connecting()

    def __getstate__(self):
        # this should get folded into ReconnectingClientFactory
        d = self.__dict__.copy()
        d['connector'] = None
        d['_callID'] = None
        return d

    # oldcred methods

    def getPerspective(self, *args):
        raise RuntimeError( "getPerspective is one-shot: use startGettingPerspective instead" )

    def startGettingPerspective(self, username, password, serviceName,
                                perspectiveName=None, client=None):
        self._doingGetPerspective = True
        if perspectiveName == None:
            perspectiveName = username
        self._oldcredArgs = (username, password, serviceName,
                             perspectiveName, client)

    def doGetPerspective(self, root):
        # oldcred getPerspective()
        (username, password,
         serviceName, perspectiveName, client) = self._oldcredArgs
        d = self._cbAuthIdentity(root, username, password)
        d.addCallback(self._cbGetPerspective,
                      serviceName, perspectiveName, client)
        d.addCallbacks(self._gotPerspective, self.failedToGetPerspective)


    # newcred methods

    def login(self, credentials, client=None):
        from Products.ZenUtils.Utils import unused
        unused(credentials, client)
        raise RuntimeError( "Login is one-shot: use startLogin instead" )

    def startLogin(self, credentials, client=None):
        self._credentials = credentials
        self._client = client
        self._doingLogin = True

    def doLogin(self, root):
        # newcred login()
        zenlog.debug("Sending credentials")
        d = self._cbSendUsername(root, self._credentials.username,
                                 self._credentials.password, self._client)
        d.addCallbacks(self._gotPerspective, self.failedToGetPerspective)
        return d

    def _gotPerspective(self, perspective):
        self._cancelConnectTimeout()
        self._cancelPingTimeout()
        self._perspective = perspective
        if self._shouldPingPerspective:
            reactor.callLater(0, self._startPingCycle)
        self.gotPerspective(perspective)


    def _disconnect(self):
        if self._broker:
            self.disconnect()
        elif self.connector:
            try:
                self.connector.disconnect()
            except Exception:
                zenlog.exception('Could not disconnect')
        else:
            zenlog.debug('No connector or broker to disconnect')

    # methods for connecting and login timeout
    def _startConnectTimeout(self, msg):
        self._cancelConnectTimeout()
        self._scheduledConnectTimeout = reactor.callLater(self._connectTimeout, self._timeoutConnect, msg)

    def _timeoutConnect(self, msg):
        zenlog.info("%s timed out after %s seconds", msg, self._connectTimeout)
        self._disconnect()

    def _cancelConnectTimeout(self):
        self._scheduledConnectTimeout, timeout = None, self._scheduledConnectTimeout
        if timeout and timeout.active():
            zenlog.debug("Cancelling connect timeout")
            timeout.cancel()

    # methods to check connection is active
    def _startPingTimeout(self):
        if not self._pingTimeout:
            self._pingTimeout = reactor.callLater(self._pingTimeoutTime,
                self._doPingTimeout)

    def _cancelPingTimeout(self):
        self._pingTimeout, timeout = None, self._pingTimeout
        if timeout and timeout.active():
            zenlog.debug("Cancelling ping timeout")
            timeout.cancel()

    def _doPingTimeout(self):
        if self._perspective:
            zenlog.warn("Perspective ping timed out after %s seconds", self._pingTimeoutTime)
            self._disconnect()

    @defer.inlineCallbacks
    def _startPingCycle(self):
        if not self._pingCheck:
            pingCheck = task.LoopingCall(self._pingPerspective)
            self._pingCheck = pingCheck
            try:
                yield pingCheck.start(self._pingInterval)
            except Exception:
                zenlog.exception("perspective ping loop died")
            finally:
                # should only happen at shutdown
                zenlog.info("perspective ping loop ended")

    @defer.inlineCallbacks
    def _pingPerspective(self):
        try:
            if self._perspective:
                zenlog.debug('pinging perspective')
                self._startPingTimeout()
                response = yield self._perspective.callRemote('ping')
                zenlog.debug("perspective %sed", response)
            else:
                zenlog.debug('skipping perspective ping')
            self._cancelPingTimeout()
        except ConnectionClosed:
            zenlog.info("Connection was closed")
            self._cancelPingTimeout()
        except Exception:
            zenlog.exception("ping perspective exception")

    # methods to override

    def connecting(self):
        """
        Called when a connection is about to be attempted. Can be the initial
        connect or a retry/reconnect
        """
        pass

    def gotPerspective(self, perspective):
        """The remote avatar or perspective (obtained each time this factory
        connects) is now available."""
        pass

    def gotRootObject(self, root):
        """The remote root object (obtained each time this factory connects)
        is now available. This method will be called each time the connection
        is established and the object reference is retrieved."""
        pass

    def failedToGetPerspective(self, why):
        """The login process failed, most likely because of an authorization
        failure (bad password), but it is also possible that we lost the new
        connection before we managed to send our credentials.
        """
        self._cancelConnectTimeout()
        zenlog.debug("ReconnectingPBClientFactory.failedToGetPerspective")
        if why.check(pb.PBConnectionLost):
            zenlog.debug("we lost the brand-new connection")
            # retrying might help here, let clientConnectionLost decide
            return

        zenlog.warning("Cancelling attempts to connect")
        self.stopTrying() # logging in harder won't help
        if why.type == 'twisted.cred.error.UnauthorizedLogin':
            zenlog.critical("zenhub username/password combination is incorrect!")
            # Don't exit as Enterprise caches info and can survive
        else:
            zenlog.critical("Unknown connection problem to zenhub %s", why.type)
