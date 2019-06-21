##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012-2019 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import os
import errno
import logging

from celery.utils import fun_takes_kwargs
from zope.dottedname.resolve import resolve

from Products.ZenUtils.celeryintegration import get_task_logger

from ..exceptions import FacadeMethodJobFailed
from .job import Job

_notfound = object()


class FacadeMethodJob(Job):
    """Use this job to execute a method on a facade."""

    name = "Products.Jobber.FacadeMethodJob"

    @classmethod
    def getJobType(cls):
        """Return a general, but brief, description of the job."""
        return "Python API"

    @classmethod
    def getJobDescription(cls, facadefqdn, method, *args, **kwargs):
        """Return a description of the job."""
        facade = facadefqdn.split(".")[-1]
        return "%s.%s %s" % (facade, method, args[0] if args else "")

    @property
    def log(self):
        """Return the logger for this job."""
        if self._log is None:
            # Get log directory, ensure it exists
            logdir = self._get_config("job-log-path")
            try:
                os.makedirs(logdir)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
            # Make the logfile path and store it in the backend for later
            # retrieval
            logfile = os.path.join(logdir, "%s.log" % self.request.id)
            self.setProperties(logfile=logfile)
            self._log = get_task_logger(self.request.id)
            self._log.setLevel(self._get_config("logseverity"))
            handler = logging.FileHandler(logfile)
            handler.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)s zen.Job: %(message)s",
            ))
            self._log.handlers = [handler]
        return self._log

    def _run(self, facadefqdn, method, *args, **kwargs):
        """Execute a facade's method.

        :param str facadefqdn: classpath to facade class.
        :param str method: name of method on facade class.
        :param *args: positional arguments to method.
        :param **kwargs: keyword arguments to method.
        :return: The return value from the method.
        :raise FacadeMethodJobFailed: method did not succeed.
        """
        facadeclass = resolve(facadefqdn)
        facade = facadeclass(self.dmd)
        bound_method = getattr(facade, method, _notfound)
        if bound_method is _notfound:
            raise FacadeMethodJobFailed(
                "No such attribute on %s: %s" % (facadeclass, method),
            )
        if not callable(bound_method):
            raise FacadeMethodJobFailed(
                "Not a callable method: %s.%s" % (facadeclass, method),
            )
        accepted = fun_takes_kwargs(bound_method, kwargs)
        kwargs = {
            k: v
            for k, v in kwargs.iteritems()
            if k in accepted
        }
        result = bound_method(*args, **kwargs)

        # Expect result = {'success': boolean, 'message': string}
        # Some old facade method jobs return None.
        if result:
            try:
                if not result["success"]:
                    raise FacadeMethodJobFailed(str(result))
                return result["message"]
            except FacadeMethodJobFailed:
                raise
            except (TypeError, KeyError):
                self.log.error(
                    "The output from job %s is not in the right format.",
                    self.request.id,
                )
