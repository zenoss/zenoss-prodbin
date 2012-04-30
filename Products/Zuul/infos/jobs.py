###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
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



