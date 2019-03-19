##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from ..config import ZenJobs
from ..exceptions import NoSuchJobException
from ..task import Abortable, DMD, ZenTask
from ..zenjobs import app

_MARKER = object()


class Job(Abortable, DMD, ZenTask):
    """Base class for jobs."""

    abstract = True  # Job class itself is not registered.

    def __new__(cls, *args, **kwargs):
        cls.summary = cls.getJobType()
        return super(Job, cls).__new__(cls, *args, **kwargs)

    @classmethod
    def getJobType(cls):
        """Return a general, but brief, description of the job.

        By default, the class type name is returned.
        """
        return cls.name

    @classmethod
    def makeSubJob(cls, args=None, kwargs=None, description=None, **options):
        """Return a celery.canvas.Signature instance.

        The Signature instance wraps the given job, its arguments, and options.
        """
        task = app.tasks.get(cls.name)
        if task is None:
            raise NoSuchJobException(
                "No job named '{}' is registered".format(cls.name),
            )
        args = args or ()
        kwargs = kwargs or {}
        # Build the task's call signature
        signature = task.s(*args, **kwargs).set(**options)
        # Add 'description' if given
        if description:
            signature = signature.set(description=description)
        return signature

    def __call__(self, *args, **kwargs):
        """Execute the job."""
        # Make the 'run' method an alias for the '_run' method, so
        # that legacy Job-based tasks match the celery.Task API.
        self.run = self._run
        return super(Job, self).__call__(*args, **kwargs)

    def setProperties(self, **properties):
        pass

    def _get_config(self, key, default=_MARKER):
        if key in ZenJobs:
            return ZenJobs.get(key)
        elif default is not _MARKER:
            return default
        else:
            raise KeyError("Config option '{}' is not defined".format(key))

    def _run(self, *args, **kw):
        raise NotImplementedError(
            "Not implemented: {0.__class__.__name__}._run".format(self),
        )
