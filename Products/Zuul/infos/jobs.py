##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from time import time
from calendar import timegm
from Products.Zuul.infos import InfoBase

class JobInfo(InfoBase):

    @property
    def uuid(self):
        return self._object.uuid

    @property
    def type(self):
        return self._object.type

    @property
    def description(self):
        return self._object.description

    @property
    def scheduled(self):
        if self._object.scheduled:
            return timegm(self._object.scheduled.timetuple())

    @property
    def started(self):
        if self._object.started:
            return timegm(self._object.started.timetuple())

    @property
    def finished(self):
        if self._object.finished:
            return timegm(self._object.finished.timetuple())

    @property
    def duration(self):
        """
        Returns, in seconds, how long this job has been running or has
        ran total if the job is finished.        
        """
        if self._object.started:
            start = self.started
            current = self.finished or time()            
            return int(current - start)

    @property
    def status(self):
        if len(self.errors):
            return "FAILURE"
        return self._object.status

    @property
    def user(self):
        return self._object.user

    @property
    def logfile(self):
        if hasattr(self._object, "logfile"):
            return self._object.logfile

    @property
    def errors(self):
        """
        Parses the logfile looking for any errors
        """
        return self._object.errors
