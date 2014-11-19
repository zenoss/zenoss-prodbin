##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging
import os
import time

import transaction
from twisted.internet.protocol import ProcessProtocol
from twisted.internet.task import LoopingCall
from twisted.internet import reactor

from Products.ZenCallHome.transport import CallHome
from Products.ZenCallHome.transport.methods.directpost import direct_post
from Products.ZenUtils.Utils import zenPath

GATHER_METRICS_INTERVAL = 60*60*24*30  # number of seconds between metrics updates

logger = logging.getLogger('zen.callhome')

class CallHomeCycler(object):
    def __init__(self, dmd):
        self.dmd = dmd
        self.callhome = CallHome(dmd).callHome
        self.gatherProtocol = None
    
    def start(self):
        LoopingCall(self.run).start(300, now=False)
    
    def run(self):
        try:
            now = long(time.time())
            self.dmd._p_jar.sync()
            
            # Start metrics gather if needed
            if (now - self.callhome.lastMetricsGather > GATHER_METRICS_INTERVAL or \
                self.callhome.requestMetricsGather) and not self.gatherProtocol:
                
                self.gatherProtocol = GatherMetricsProtocol()
                self.callhome.requestMetricsGather = True
            
            # Update metrics if run complete
            if self.gatherProtocol and (self.gatherProtocol.data or self.gatherProtocol.failed):
                if not self.gatherProtocol.failed:
                    self.callhome.metrics = self.gatherProtocol.data
                self.callhome.lastMetricsGather = now
                self.callhome.requestMetricsGather = False
                self.gatherProtocol = None
            
            # Callhome directly if needed
            direct_post(self.dmd)
            
            transaction.commit()
        except Exception as e:
            logger.debug("Callhome cycle failed: '%r'", e)


class GatherMetricsProtocol(ProcessProtocol):
    def __init__(self):
        self.data = None
        self.failed = False
        self.output = []
        self.error = []
        chPath = zenPath('Products', 'ZenCallHome', 'callhome.py')
        reactor.spawnProcess(self, 'python', args=['python', chPath, '-M'],
                             env=os.environ)

    def outReceived(self, data):
        self.output.append(data)

    def errReceived(self, data):
        self.error.append(data)
    
    def processEnded(self, reason):
        out = ''.join(self.output)
        err = ''.join(self.error)
        if reason.value.exitCode != 0:
            self.failed = True
            logger.warning('Callhome metrics gathering failed: stdout: %s, stderr: %s', out, err)
        else:
            self.data = out
