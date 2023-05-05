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
        title=six.text_type("Job ID"),
        description=six.text_type("The Job's unique identifier"),
    )

    name = TextLine(
        title=six.text_type("Name"),
        description=six.text_type("The full class name of the job"),
    )

    summary = TextLine(
        title=six.text_type("Summary"),
        description=six.text_type(
            "A brief and general summary of the job's function"
        ),
    )

    description = TextLine(
        title=six.text_type("Description"),
        description=six.text_type("A description of what this job will do"),
    )

    userid = TextLine(
        title=six.text_type("User ID"),
        description=six.text_type("The user that created the job"),
    )

    logfile = TextLine(
        title=six.text_type("Logfile"),
        description=six.text_type("Path to this job's log file."),
    )

    status = Choice(
        title=six.text_type("Status"),
        description=six.text_type("The current status of the job"),
        vocabulary=SimpleVocabulary.fromValues(states.ALL_STATES),
    )

    created = Datetime(
        title=six.text_type("Created"),
        description=six.text_type("When the job was created"),
    )

    started = Datetime(
        title=six.text_type("Started"),
        description=six.text_type("When the job began executing"),
    )

    finished = Datetime(
        title=six.text_type("Finished"),
        description=six.text_type("When the job finished executing"),
    )

    duration = Timedelta(
        title=six.text_type("Duration"),
        description=six.text_type("How long the job has run"),
    )

    complete = Bool(
        title=six.text_type("Complete"),
        description=six.text_type("True if the job has finished running"),
    )

    def abort():
        """Abort the job."""

    def wait(timeout=10.0):
        """Wait until the job has completed or the timeout duration has
        been exceeded before returning.
        """


class IJobStore(Interface):
    """Interface tag for JobStore."""
