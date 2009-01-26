###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import os
import time
import transaction
from twisted.internet import defer, reactor
from twisted.internet.protocol import ProcessProtocol
from zope.interface import implements
from Globals import InitializeClass
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.Utils import basicAuthUrl, zenPath
from Products.ZenWidgets import messaging

from interfaces import IJob
from status import SUCCESS, FAILURE
from logfile import LogFile
import time

class Job(ZenModelRM):

    implements(IJob)

    _relations = (
        ("status", ToOne( ToOne, "Products.Jobber.status.JobStatus", "job")),
    )

    def getDescription(self):
        return self.id

    def getJobType(self):
        return self.__class__.__name__

    def getStatus(self):
        """
        @return: The L{JobStatus} associated with this job.
        @rtype: L{JobStatus}
        """
        return self.status()

    def interrupt(self, why):
        """
        Halt the job, for whatever reason.

        This will almost certainly be implemented differently in various
        subclasses.

        @param why: The reason why the build is interrupted
        @type why: str
        """
        pass

    def start(self):
        """
        This starts off the build. Returns a Deferred that will fire when the
        step finishes.
        """
        whendone = defer.Deferred()
        self._v_deferred = whendone
        status = self.getStatus()
        if status is not None:
            status.jobStarted()
        d = defer.succeed(None)
        d.addCallback(self.run)
        return whendone

    def run(self, r):
        """
        Should call self.finished(results) when done, where results is one of
        SUCCESS, FAILURE.
        """
        raise NotImplementedError("Your subclass must implement this method.")

    def finished(self, results):
        """
        Called to signify the end of the job.
        """
        d = self._v_deferred
        # Tell the JobStatus we're done
        status = self.getStatus()
        if status is not None:
            status.jobFinished(results)
        # Call back to the self.start() Deferred
        d.callback(results)


class ProcessRunner(ProcessProtocol):
    log = None
    def __init__(self, job, whenComplete):
        """
        Initialization method. Accepts a reference to the relevant Job
        instance and a defer.Deferred that will be called back.
        """
        self.job = job
        self.whenComplete = whenComplete

    def getLog(self):
        """
        Return the log for the status for the job.
        """
        if self.log is None:
            status = self.job.getStatus()
            if status is not None:
                self.log = status.getLog()
        return self.log

    def outReceived(self, text):
        """
        Send output to the log file
        """
        log = self.getLog()
        if log is not None:
            log.write(text)

    # Send error to same place as other output
    errReceived = outReceived

    def processEnded(self, reason):
        """
        We're done. End the job.
        """
        if self.log is not None:
            self.log.finish()
        code = 1
        try:
            code = reason.value.exitCode
        except AttributeError:
            pass
        if code==0:
            result = SUCCESS
        else:
            result = FAILURE
        self.whenComplete.callback(result)


class ShellCommandJob(Job):
    _v_process = None
    pid = 0
    def __init__(self, jobid, cmd):
        """
        Initialization method.

        @param cmd: The command that will be run by the job.
        @type cmd: list or string
        """
        super(ShellCommandJob, self).__init__(jobid)
        if isinstance(cmd, basestring):
            cmd = cmd.split()
        self.cmd = cmd
        # We could conceivably want to know the environment in the future, so
        # keep it around
        self.environ = os.environ.copy()

    def getDescription(self):
        return " ".join(self.cmd)

    def run(self, r):
        cmd = self.cmd
        d = defer.Deferred()
        protocol = ProcessRunner(self, d)
        self._v_process = reactor.spawnProcess(protocol, cmd[0], cmd, 
                            env=self.environ, usePTY=True)
        self.pid = self._v_process.pid
        transaction.commit()
        d.addBoth(self.finished)

    def interrupt(self):
        # If we're still in the reactor, use the PTYProcess. This will probably
        # never happen.
        if self._v_process is not None:
            self._v_process.signalProcess('STOP')
        # Our only hope is still having a pid
        elif self.pid:
            try: os.kill(self.pid, 15)
            except OSError: pass # We can't do anything else anyway


class JobMessenger(messaging.MessageSender):
    """
    Adapts IJobs to send messages. Differs from MessageSender insofar as it
    forces a commit to the database after sending.
    """
    def sendToBrowser(self, *args, **kwargs):
        super(JobMessenger, self).sendToBrowser(*args, **kwargs)
        transaction.commit()

    def sendToUser(self, *args, **kwargs):
        super(JobMessenger, self).sendToUser(*args, **kwargs)
        transaction.commit()

    def sendToAll(self, *args, **kwargs):
        super(JobMessenger, self).sendToAll(*args, **kwargs)
        transaction.commit()

