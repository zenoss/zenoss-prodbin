##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from twisted.internet import reactor, defer
from twisted.internet.error import ProcessExitedAlready
from twisted.internet.protocol import ProcessProtocol
from twisted.python.failure import Failure

from zope.interface import Interface, Attribute, implements

from Products.DataCollector.SshClient import SshClient
from Products.ZenUtils.Utils import DictAsObj
from Products.ZenCollector.pools import getPool

log = logging.getLogger("zen.runner")


class TimeoutError(Exception):
    def __init__(self, *args):
        super(TimeoutError, self).__init__()
        self.args = args


def getRunner(proxy=None, client=None, connection=None):

    if client and issubclass(client, SshRunner.client):
        runner = SshRunner(proxy, client)
        runner.connection = connection
    else:
        runner = ProcessRunner()
    return runner


class IRunner(Interface):
    connection = Attribute("Object describing the client connection")
    client = Attribute("Client connection class")
    proxy = Attribute("Connection information about a device")
    exitCode = Attribute("The resulting exitcode from the given command")
    output = Attribute("Result of standard out")
    stderr = Attribute("Result of standard error")

    def connect(self, task):
        """
        Establishes a connection through the connection client
        """

    def send(self, command):
        """
        Send a command through the connection
        """

    def close(self):
        """
        Closes the connection to the client
        """


class IClient(Interface):
    """
    Interface for supporting client connection objects
    """
    connect_defer = Attribute("Deferred for establishing a connection")
    command_defers = Attribute("Deferreds for submitting commands")
    close_defer = Attribute("Deferred for a closed connection")
    description = Attribute("String describing connection information")
    tasks = Attribute("Set of tasks associated with a connection")
    is_expired = Attribute("Boolean to mark an expired connection")


class ProcessRunner(ProcessProtocol):
    implements(IRunner)

    connection = None
    client = None
    proxy = None
    exitCode = None
    output = []
    stderr = []

    def connect(self, task=None):
        """
        Commands are run locally, so this is simply a passthrough
        """
        log.debug("Running command(s) locally")
        return defer.succeed(None)

    def send(self, command):
        """
        Kick off the process
        """
        log.debug("Running %s", command.command.split()[0])
        shell = "/bin/sh"
        cmdline = (shell, '-c', 'exec %s' % command.command)

        self.command = command
        self.stdin = ' '.join(cmdline)

        commandTimeout = command.deviceConfig.zCommandCommandTimeout
        d = self.command_defer = defer.Deferred()
        reactor.spawnProcess(self, shell, cmdline, env=command.env)
        self._timer = reactor.callLater(commandTimeout, self.timeout)

        return d

    def close(self, *args):
        pass

    def timeout(self, timedOut=True):
        """
        Kill a process gracefully if it takes too long
        """
        if not self.command_defer.called:
            if timedOut:
                self.command_defer.errback(TimeoutError(self.command))
            try:
                self.transport.signalProcess("INT")
                reactor.callLater(2, self._reap)
            except ProcessExitedAlready:
                log.debug("Command already exited: %s", self.stdin.split()[0])

    def _reap(self):
        """
        Kill a process forcefully if it takes too long
        """
        try:
            self.transport.signalProcess("KILL")
        except Exception:
            pass

    def outReceived(self, data):
        """
        Stores the result of stdout as it arrives from the process
        """
        self.output.append(data)

    def errReceived(self, data):
        """
        Stored the result of stderr as it arrives from the process
        """
        self.stderr.append(data)

    def processEnded(self, reason):
        """
        Notify the started that the process is complete
        """
        self.exitCode = reason.value.exitCode
        if self.exitCode is not None:
            self._timer.cancel()
            self.output = ''.join(self.output)
            self.stderr = ''.join(self.stderr)

            msg = "Datasource: %s Received exit code: %s Output: \n%r"
            data = self.command.ds, self.exitCode, self.output
            if self.stderr:
                msg += "\nStandard Error:\n%r"
                data.append(self.stderr)
            log.debug(msg, *data)

        d, self.command_defer = self.command_defer, None
        if not d.called:
            d.callback(self)


class SshRunner(object):
    implements(IRunner)

    POOLNAME = "SSH Connections"
    EXPIRED_MESSAGES = ("WARNING: Your password has expired.\nPassword" \
        " change required but no TTY available.\n",)

    connection = None
    client = SshClient
    proxy = None
    exitCode = None
    output = ""
    stderr = ""

    def __init__(self, proxy, client):
        self.proxy = proxy
        self.client = client

        self.task = None
        self.deviceId = self.proxy.id
        self.manageIp = self.proxy.manageIp
        self.port = self.proxy.zCommandPort

        _username = self.proxy.zCommandUsername
        _password = self.proxy.zCommandPassword
        _loginTimeout = self.proxy.zCommandLoginTimeout
        _commandTimeout = self.proxy.zCommandCommandTimeout
        _keyPath = self.proxy.zKeyPath
        _concurrentSessions = self.proxy.zSshConcurrentSessions

        self._sshOptions = DictAsObj(
            loginTries=1,
            searchPath='',
            existenceTest=None,
            username=_username,
            password=_password,
            loginTimeout=_loginTimeout,
            commandTimeout=_commandTimeout,
            keyPath=_keyPath,
            concurrentSessions=_concurrentSessions,
        )
        self._poolkey = hash((_username, _password, self.manageIp, self.port))
        self._pool = getPool(SshRunner.POOLNAME)

    @defer.inlineCallbacks
    def connect(self, task):
        """
        Establish a connection with the device
        """
        self.task = task
        self._setupConnector()
        self.connection = yield self._establishConnection()
        log.debug("Connected to %s [%s]", self.deviceId, self.manageIp)
        self.connection.tasks.add(self.task)
        self.connection.close_defer.addCallback(self.cleanUpPool)

    @defer.inlineCallbacks
    def _setupConnector(self):
        """
        Create a new connection object for the pool if it doesn't exist.
        Set up a list for storing deferred objects that will callback
        or errback based on the result of the initial deferred.
        """
        if self._poolkey not in self._pool:
            log.debug("Creating connection object to %s", self.deviceId)
            connection = self.client(self.deviceId, self.manageIp, self.port,
                                     options=self._sshOptions)
            self._pool[self._poolkey] = []

            try:
                connection = yield connection.run()
            except Exception, e:
                deferredList = self._pool.get(self._poolkey, [])
                self.cleanUpPool(connection)
                for d in deferredList:
                    d.errback(e)
            else:
                deferredList = self._pool.get(self._poolkey, [])
                self._pool[self._poolkey] = connection
                for d in deferredList:
                    d.callback(connection)

    def _establishConnection(self):
        """
        Either creates a deferred to append to the pool list otherwise, wraps
        the result
        """

        if isinstance(self._pool[self._poolkey], list):
            d = defer.Deferred()
            self._pool[self._poolkey].append(d)
        else:
            d = defer.succeed(self._pool[self._poolkey])

        return d

    def send(self, command):
        """
        Create a channel on the connection and send the command
        """
        self.command = command
        d = self.command_defer = self.connection.addCommand(command.command)
        self._timer = reactor.callLater(self._sshOptions.commandTimeout,
                                        self.timeout)
        d.addBoth(self.processEnded)
        return d

    def close(self):
        """
        Discard the task and close the connection if there are no remaining
        tasks
        """
        if self.connection:
            self.connection.tasks.discard(self.task)
            if not self.connection.tasks:
                self.connection.clientFinished()
                if not self.connection.is_expired:
                    self.cleanUpPool()
            self.connection = None

    def timeout(self, timedOut=True):
        """
        Deal with slow executing commmand/connection (close it)
        We could send a kill signal, but then we would need to track the
        command channel to send it.  Just close the connection instead
        """
        if not self.command_defer.called:
            self.command_defer.errback(TimeoutError(self.command))

    def cleanUpPool(self, connection=None):
        """
        Deletes the connection from the pool (if it exists)
        """
        connection = connection or self.connection

        if self._poolkey in self._pool:
            log.debug("Deleting connection %s from pool",
                      connection.description)
            del self._pool[self._poolkey]

    def processEnded(self, result):
        """
        Deliver ourselves to the starter with the proper attributes
        """
        if isinstance(result, Failure):
            return result

        self._timer.cancel()
        self.output, self.exitCode, self.stderr = result

        if not self.connection.is_expired \
                and self.stderr in SshRunner.EXPIRED_MESSAGES:

            log.debug('Connection %s expired, cleaning up pool', 
                self.connection.description)
            self.connection.is_expired = True
            self.cleanUpPool()

        return self
