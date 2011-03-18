###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from math import fsum, sqrt, pow
import logging
log = logging.getLogger("zen.PingJob")

from twisted.internet import defer

class PingJob(object):
    """
    Class representing a single target to be pinged.
    """
    def __init__(self, ipaddr, hostname="", status=0,
                 unused_cycle=60, maxtries=2, sampleSize=1,
                 iface=''):
        self.ipaddr = ipaddr 
        self.iface = iface 
        self.hostname = hostname
        self.status = status
        self.maxtries = maxtries
        self.sampleSize = sampleSize
        self.points = []  # For storing datapoints
        self.reset()

    def reset(self):
        self.deferred = defer.Deferred()
        self.start = 0
        self.sent = 0
        self.rcvCount = 0
        self.loss = 0
        self.message = ""
        self.severity = 5
        self.inprocess = False

        self.results = []
        self.rtt = 0
        self.rtt_max = 0.0
        self.rtt_min = 0.0
        self.rtt_avg = 0.0
        self.rtt_stddev = 0.0
        self.rtt_losspct = 0.0

    def calculateStatistics(self):
        n = len(self.results)
        if n == 0:
            return

        elif n == 1:
            self.rtt_avg = self.rtt
            self.rtt_max = self.rtt
            self.rtt_min = self.rtt
            self.rtt_stddev = 0.0
            return

        total = fsum(self.results)
        self.rtt_avg = total / n
        self.rtt_stddev = self.stdDev(self.rtt_avg)

        self.rtt_min = min(self.results)
        self.rtt_max = max(self.results)

        self.rtt_losspct = ((self.sent - self.loss) / self.sent) * 100

    def stdDev(self, avg):
        """
        Calculate the sample standard deviation.
        """
        n = len(self.results)
        if n < 1:
            return 0
        # sum of squared differences from the average
        total = fsum( map(lambda x: pow(x - avg, 2), self.results) )
        # Bessel's correction uses n - 1 rather than n
        return sqrt( total / (n - 1) )

    def __str__(self):
        return "%s %s" % (self.hostname, self.ipaddr)

