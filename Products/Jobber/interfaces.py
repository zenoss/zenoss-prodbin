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

from zope.interface import Interface

class IJob(Interface):
    """
    Persistent object that contains the entry-point function for running a job.
    """
    def start():
        """
        Begins the job-running process. Does setup, then calls self.run().
        """
    def run():
        """
        Contains all job-specific code. This will be overridden in subclasses
        to provide the ability to run different kinds of jobs.
        """
    def finished(results):
        """
        Called when the job is finished.
        """
    def interrupt(why):
        """
        Halt the running of the job. If necessary, send signals to any
        subprocesses that are involved in job running.
        """
    def update(msg):
        """
        Set the current status of the running job to C{msg}.
        """
    def getStatus():
        """
        Get the L{IJobStatus} associated with this job.
        """

class IJobStatus(Interface):
    """
    Contains interesting information about a job, including state, start and
    finish times, and log file.
    """
    def getJob():
        """
        Return the IJob associated with this status object.
        """
    def getTimes():
        """
        Returns a (start, end) tuple, indicating when the Job started and
        finished. If the Job is still running, end will be None.
        """
    def getLog():
        """
        Return the ILogFile that contains the job output.
        """
    def isFinished():
        """
        Return a boolean indicating whether or not the job has finished.
        """
    def waitUntilFinished():
        """
        Return a Deferred that will fire when the IJob finishes. If the IJob
        has finished, this Deferred will fire right away.
        """
    def getResult():
        """
        Return a constant describing the results of the job, from jobs.status:
        SUCCESS or FAILURE.
        """

class IJobManager(Interface):
    """
    Provides a hub for the job subsystem. Can be queried to find the status of
    running or previous jobs. Jobs are created from here.
    """
    def addJob(klass):
        """
        Create an instance of C{klass}, which must implement L{IJob}.

        @return: A Job instance.
        @rtype: IJob
        """
    def getJobStatus(job):
        """
        Return the IJobStatus for a given IJob or job id.
        """
    def getUnfinishedJobs():
        """
        Return IJobStatus objects that have yet to finish.
        """
    def getRunningJobs():
        """
        Return IJobStatus objects that have started and have yet to finish.
        """
    def getPendingJobs():
        """
        Return IJobStatus objects that have yet to start.
        """

class IJobLogFile(Interface):
    """
    Job output of any kind.
    """
    def write(data):
        """
        Write C{data} to the Log.
        """
    def finish():
        """
        No further data will be added to the log file, so close it and notify
        anyone who cares.
        """
    def subscribe(subscriber, catchup=False):
        """
        Register to receive output as data is added to the log. If catchup is
        True, log contents up to that point will be returned immediately to the
        receiver.

        @param subscriber: The receiver of data as it comes in
        @type subscriber: file-like
        """
    def unsubscribe(subscriber):
        """
        Remove a previously registered subscriber.
        """
    def getStatus():
        """
        Return the IJobStatus that owns this log.
        """
    def getFilename():
        """
        Return the filename of the file on disk containing the log data.
        """
    def isFinished():
        """
        Return a boolean indicating whether or not the log has finished.
        """
    def waitUntilFinished():
        """
        Return a Deferred that will fire when the log finishes. If the log has
        finished, this Deferred will fire right away.
        """

