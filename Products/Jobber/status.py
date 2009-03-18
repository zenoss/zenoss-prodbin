from Globals import InitializeClass
from Products.ZenRelations.RelSchema import *
from Products.ZenModel.ZenModelRM import ZenModelRM
import os
import sys
import time
import copy
import logging
from zope.interface import implements
from twisted.internet import defer
from twisted.spread import pb
from interfaces import IJobStatus
from logfile import LogFile
import tempfile
import transaction

SUCCESS = 0
FAILURE = 1

class JobStatus(ZenModelRM):

    implements(IJobStatus)

    _relations = (
       ("jobmanager",
         ToOne(
           ToManyCont, "Products.Jobber.manager.JobManager", "jobs"
         )
       ),
       ("job",
         ToOne(
           ToOne, "Products.Jobber.jobs.Job", "status"
         )
       ),
    )

    started = None    # Start time
    finished = None   # Finish time
    result = None
    filename = None
    properties = None

    def __init__(self, job):
        if self.properties is None:
            self.properties = {}

        self.filename = tempfile.mktemp()
        transaction.commit()
        self.finishDeferreds = []

        id = job.id.replace('_', 'Status_')
        super(JobStatus, self).__init__(id)

        # Set up references to the job
        self.addRelation('job', job)

    def getUid(self):
        return self.id.split('_')[-1]

    def getLogFileName(self):
        try:
            self._p_jar.sync()
        except AttributeError: 
            # No database, probably a unit test
            pass
        return self.filename

    def getLog(self):
        return LogFile(self, self.getLogFileName())

    def getJob(self):
        return self.job()

    def getTimes(self):
        return (self.started, self.finished)

    def getDuration(self):
        if self.isFinished():
            return self.finished - self.started

    def setProperties(self, **props):
        self.properties.update(props)
        self._p_changed = True

    def getProperties(self):
        return copy.deepcopy(self.properties)

    def setZProperties(self, **zprops):
        self.properties.setdefault('zProperties', {}).update(zprops)
        self._p_changed = True

    def getResult(self):
        return self.result

    def isStarted(self):
        return (self.started is not None)

    def isFinished(self):
        return (self.finished is not None)

    def waitUntilFinished(self):
        if self.finished:
            d = defer.succeed(self)
        else:
            d = defer.Deferred()
            self.finishDeferreds.append(d)
        return d

    def jobStarted(self):
        self.started = time.time()

    def jobFinished(self, result):
        """
        Called by the Job when it's done. C{result} should be SUCCESS or
        FAILURE.
        """
        self.finished = time.time()
        self.result = result
        # Call back to everything watching this Job
        for d in self.finishDeferreds:
            d.callback(self)
        del self.finishDeferreds

    def delete(self):
        # Clean up the log file
        fn = self.getLogFileName()
        if fn and os.path.exists(fn):
            os.remove(fn)
        # Remove the job status itself
        parent = self.getPrimaryParent()
        parent._delObject(self.id)


InitializeClass(JobStatus)


class JobStatusProxy(pb.Copyable, pb.RemoteCopy):
    """
    Represents a JobStatus object in a daemon.
    """
    id = None
    _properties = None

    def __init__(self, jobstatus):
        self.id = jobstatus.id.split('_')[-1]
        self._properties = jobstatus.getProperties()

    def get(self, key, default=None):
        return self._properties.get(key, default)

    def __getitem__(self, name):
        return self._properties[name]

    def __getattr__(self, attr):
        return self[attr]

    def getProperties(self):
        return copy.deepcopy(self._properties)

pb.setUnjellyableForClass(JobStatusProxy, JobStatusProxy)

