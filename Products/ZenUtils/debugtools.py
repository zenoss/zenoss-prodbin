###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
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


