###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import zope.component
import sys
from Products.ZenUtils.CmdBase import CmdBase
from Products.ZenCollector.interfaces import IWorkerExecutor, IWorkerTaskFactory
from Products.ZenCollector.tasks import SimpleTaskSplitter
from Products.ZenCollector.daemon import CollectorDaemon

class CollectorCmdBase(CmdBase):

    def __init__(self, iCollectorWorkerClass, iCollectorPreferencesClass, noopts=0, args=None):
        super(CollectorCmdBase, self).__init__(noopts, args)
        self.workerClass = iCollectorWorkerClass
        self.prefsClass = iCollectorPreferencesClass

    def run(self):
        if "--worker" in sys.argv:
            executor = zope.component.getUtility(IWorkerExecutor)
            executor.setWorkerClass(self.workerClass)
            executor.run()
        else:
            myPreferences = self.prefsClass()
            myTaskFactory = zope.component.getUtility(IWorkerTaskFactory)
            myTaskFactory.setWorkerClass(self.workerClass)
            myTaskSplitter = SimpleTaskSplitter(myTaskFactory)
            daemon = CollectorDaemon(myPreferences, myTaskSplitter)
            myTaskFactory.postInitialization()
            self.log = daemon.log
            daemon.run()
