##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os
import hotshot
import hotshot.stats
import tempfile

class Profiler(object):

    def __init__(self):
        self.fname = tempfile.mktemp()
        self.profiler = hotshot.Profile(self.fname, True)

    def print_stats(self, limit=20):
        stats = hotshot.stats.load(self.fname)
        stats.sort_stats('time', 'calls')
        stats.print_stats(limit)

    def runcall(self, *args, **kwargs):
        result = self.profiler.runcall(*args, **kwargs)
        self.profiler.close()
        return result

    def __del__(self):
        os.remove(self.fname)


def profile(f):
    """
    Decorator that will profile a function and print stats.
    """
    def inner(*args, **kwargs):
        p = Profiler()
        result = p.runcall(f, *args, **kwargs)
        p.print_stats()
        return result
    return inner
