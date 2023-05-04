##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import six

from celery import states
from zope.interface import Interface
from zope.schema import Bool, Choice, Datetime, TextLine, Timedelta
from zope.schema.vocabulary import SimpleVocabulary


class IJobRecord(Interface):
    """ """

    jobid = TextLine(
        title=six.u("Job ID"),
        description=six.u("The Job's unique identifier"),
    )

    name = TextLine(
        title=six.u("Name"),
        description=six.u("The full class name of the job"),
    )

    summary = TextLine(
        title=six.u("Summary"),
        description=six.u("A brief and general summary of the job's function"),
    )

    description = TextLine(
        title=six.u("Description"),
        description=six.u("A description of what this job will do"),
    )

    userid = TextLine(
        title=six.u("User ID"),
        description=six.u("The user that created the job"),
    )

    logfile = TextLine(
        title=six.u("Logfile"),
        description=six.u("Path to this job's log file."),
    )

    status = Choice(
        title=six.u("Status"),
        description=six.u("The current status of the job"),
        vocabulary=SimpleVocabulary.fromValues(states.ALL_STATES),
    )

    created = Datetime(
        title=six.u("Created"), description=six.u("When the job was created")
    )

    started = Datetime(
        title=six.u("Started"),
        description=six.u("When the job began executing"),
    )

    finished = Datetime(
        title=six.u("Finished"),
        description=six.u("When the job finished executing"),
    )

    duration = Timedelta(
        title=six.u("Duration"), description=six.u("How long the job has run")
    )

    complete = Bool(
        title=six.u("Complete"),
        description=six.u("True if the job has finished running"),
    )

    def abort():
        """Abort the job."""

    def wait(timeout=10.0):
        """Wait until the job has completed or the timeout duration has
        been exceeded before returning.
        """


class IJobStore(Interface):
    """Interface tag for JobStore."""
