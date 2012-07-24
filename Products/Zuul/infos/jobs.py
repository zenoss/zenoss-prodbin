##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


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
        return timegm(self._object.scheduled.timetuple())

    @property
    def started(self):
        return timegm(self._object.started.timetuple())

    @property
    def finished(self):
        return timegm(self._object.finished.timetuple())

    @property
    def status(self):
        return self._object.status

    @property
    def user(self):
        return self._object.user
