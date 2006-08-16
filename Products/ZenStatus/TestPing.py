#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

from AsyncPing import PingJob
from twisted.internet import reactor
import os.path
import time

class Ping(object):
    def __init__(self, *args):
        self.count = 0

    def jobCount(self):
        return self.count
    
    def sendPacket(self, pj):
        self.count += 1
        pj.reset()
        pj.start = time.time()
        if not os.path.exists('/tmp/testping'):
            reactor.callLater(0, self.bad, pj)
        else:
            for line in file('/tmp/testping'):
                if line.strip() == pj.ipaddr:
                    reactor.callLater(0, self.good, pj)
                    break
            else:
                reactor.callLater(0, self.bad, pj)

    def good(self, pj):
        self.count -= 1
        pj.deferred.callback(pj)

    def bad(self, pj):
        self.count -= 1
        pj.deferred.errback(pj)
