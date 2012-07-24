##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


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
