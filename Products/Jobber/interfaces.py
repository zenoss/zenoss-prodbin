##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from celery import states
from zope.interface import Interface
from zope.schema import Bool, Choice, Datetime, TextLine, Timedelta
from zope.schema.vocabulary import SimpleVocabulary


class IJobRecord(Interface):
    """
    """

    jobid = TextLine(
        title=u"Job ID",
        description=u"The Job's unique identifier",
    )

    name = TextLine(
        title=u"Name",
        description=u"The full class name of the job",
    )

    summary = TextLine(
        title=u"Summary",
        description=u"A brief and general summary of the job's function",
    )

    description = TextLine(
        title=u"Description",
        description=u"A description of what this job will do",
    )

    userid = TextLine(
        title=u"User ID",
        description=u"The user that created the job",
    )

    logfile = TextLine(
        title=u"Logfile",
        description=u"Path to this job's log file.",
    )

    status = Choice(
        title=u"Status",
        description=u"The current status of the job",
        vocabulary=SimpleVocabulary.fromValues(states.ALL_STATES),
    )

    created = Datetime(
        title=u"Created",
        description=u"When the job was created"
    )

    started = Datetime(
        title=u"Started",
        description=u"When the job began executing"
    )

    finished = Datetime(
        title=u"Finished",
        description=u"When the job finished executing"
    )

    duration = Timedelta(
        title=u"Duration",
        description=u"How long the job has run"
    )

    complete = Bool(
        title=u"Complete",
        description=u"True if the job has finished running",
    )

    def abort():
        """Abort the job.
        """

    def wait(timeout=10.0):
        """Wait until the job has completed or the timeout duration has
        been exceeded before returning.
        """


class IJobStore(Interface):
    """Interface tag for JobStore.
    """
