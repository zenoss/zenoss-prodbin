##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import cProfile
import pstats
import tempfile

class Profiler(object):

    def __init__(self):
        self._stats = None

    @property
    def stats(self):
        return self._stats

    def print_stats(self, limit=20):
        if self._stats:
            self._stats.sort_stats('time', 'calls')
            self._stats.print_stats(limit)

    def runcall(self, func, *args, **kwargs):
        profile = cProfile.Profile()
        result = profile.runcall(func, *args, **kwargs)
        statsfile = tempfile.NamedTemporaryFile()
        try:
            profile.dump_stats(statsfile.name)
            self._stats = pstats.Stats(statsfile.name)
        finally:
            statsfile.close()
        return result


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


def rpdb_set_trace(log=None):
    """
    convenience function to set_trace with rpdb in a control center container
    """
    import rpdb
    import subprocess

    ip=subprocess.check_output(["hostname", "-i"]).strip()
    port=4444
    print "connect to rpdb remotely with: nc %s %d  # Control-C to exit nc" % (ip, port)
    if log:
        log.warn("connect to rpdb remotely with: nc %s %d  # Control-C to exit nc" % (ip, port))
    debugger = rpdb.Rpdb(ip, port)
    debugger.set_trace()

