###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Products.Five.browser import BrowserView
from Products.ZenMessaging.audit import audit

class ManageJobView(BrowserView):
    """
    Provides a management API for jobs.
    """
    def delete(self):
        self.context.delete()

    def interrupt(self):
        job = self.context.getJob()
        job.interrupt()
        audit('UI.Job.Stop', job.id)
