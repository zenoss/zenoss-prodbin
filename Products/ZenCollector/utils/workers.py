###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import multiprocessing
import logging
import signal
import os
import sys

from twisted.internet import reactor
from Products.ZenUtils.CmdBase import remove_args

log = logging.getLogger("zen.workers")


def workersBuildOptions(parser, default=1):
    """
    Adds option for number or workers
    """
    parser.add_option('--workers',
                      type="int",
                      default=default,
                      help="The number of processing workers to run "
                           "(ignored when running in the foreground)")

def exec_worker():
    """
    used to create a worker for an existing zenoss daemon. Removes the
    "workers" and "daemon" sys args and replace the current process by
    executing sys args
    """
    argv = [sys.executable]
    # Remove unwanted parameters from worker processes
    argv.extend(remove_args(sys.argv[:], ['-D','--daemon'], ['--workers']))
    # Tell the worker process to log to the log file and not just to console
    argv.append('--duallog')
    try:
        os.execvp(argv[0], argv)
    except:
        log.exception("Failed to start process")

class ProcessWorkers(object):
    """
    class for starting and restarting Multiprocessing process from
    withing a twisted reactor
    """
    def __init__(self, maxWorkers, workerTarget, workerName=None):
        self._maxWorkers = maxWorkers
        self._workerTarget = workerTarget
        self._workerName = workerName
        #keeps track of number of workers started and restarted
        self._workerCount = 0
        self._workers = []
        self._checking=False
        self._shutdown = False

    def _sigchldhandler(self, signum=None, frame=None):
        if not self._shutdown:
            log.debug("_sigchldhandler reactor checkworkers")
            reactor.callLater(1, self.checkWorkers)
        else:
            log.debug("_sigchldhandler: shutting down, skipping")

        
    def startWorkers(self):
        def _doStart():
            for i in xrange(self._maxWorkers):
                self._startWorker()
            log.debug("Registering SIGCHLD handler")
            signal.signal(signal.SIGCHLD, self._sigchldhandler)
        reactor.callWhenRunning(_doStart)


    def shutdown(self):
        self._shutdown = True
        for worker in self._workers:
            log.info("stopping worker %s..." % worker)
            worker.terminate()
            worker.join()
        self._workers = []

    def checkWorkers(self, *args):
        log.debug("checkWorkers method")
        if self._checking:
            log.debug("already checking")
            return
        try:
            self._checking = True
            log.debug("checking workers: current %s, max %s"%(len(self._workers), self._maxWorkers))
            currentWorkers = []
            currentWorkers.extend(self._workers)
            for worker in currentWorkers:
                if not worker.is_alive():
                    log.info("worker %s is dead" % worker)
                    self._workers.remove(worker)
            while len(self._workers) < self._maxWorkers:
                log.debug("starting worker...")
                self._startWorker()
        finally:
            self._checking = False
            
    def _startWorker(self):
        self._workerCount +=1
        workerName = None
        if self._workerName:
            workerName = '%s %s' % (self._workerName, self._workerCount)
        log.debug('starting worker %s' % workerName)
        p = multiprocessing.Process(
            target=self._workerTarget,
            name=workerName
            )
        p.daemon = True
        p.start()
        log.info("Started worker %s: pid=%s", (p,p.pid))
        self._workers.append(p)