###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import unittest
import time
import subprocess
from StringIO import StringIO

from twisted.internet import reactor

from Products.Jobber.interfaces import *
from Products.Jobber.jobs import Job, ShellCommandJob
from Products.Jobber.manager import JobManager
from Products.Jobber.status import JobStatus, SUCCESS, FAILURE
from Products.Jobber.logfile import LogFile

class SucceedingJob(Job):
    def run(self, r):
        self.finished(SUCCESS)

class FailingJob(Job):
    def run(self, r):
        self.finished(FAILURE)

class NotAJob(object):
    def run(self):
        pass

class OneSecondJob(Job):
    def run(self, r):
        def done():
            self.finished(SUCCESS)
        reactor.callLater(1, done)


class TestJob(unittest.TestCase):

    def test_id_required(self):
        self.assertRaises(TypeError, Job)

    def test_step_workflow(self):
        """
        Make sure that if start() is called, it makes its way through run() and
        finished() with the proper result at the end.
        """
        def test_success(result): self.assertEqual(result, SUCCESS)
        def test_failure(result): self.assertEqual(result, FAILURE)

        good = SucceedingJob('good')
        bad = FailingJob('bad')

        d = good.start()
        d.addCallback(test_success)

        d = bad.start()
        d.addCallback(test_failure)


class TestJobStatus(unittest.TestCase):
    def setUp(self):
        self.j = JobStatus(Job('ajob'))

    def test_isFinished(self):
        self.assertEqual(self.j.isFinished(), False)

        self.j.jobStarted()
        self.assertEqual(self.j.isFinished(), False)

        self.j.jobFinished(None)
        self.assertEqual(self.j.isFinished(), True)

    def test_waitUntilFinished(self):
        self.j.jobStarted()
        def hasFinished(jobstatus):
            self.assert_(jobstatus.isFinished())
        d = self.j.waitUntilFinished()
        d.addCallback(hasFinished)
        self.j.jobFinished(SUCCESS)


class TestJobManager(unittest.TestCase):
    def setUp(self):
        self.m = JobManager('jobmgr')

    def test_add_job_jobs_only(self):
        self.assertRaises(AssertionError, self.m.addJob, NotAJob)

    def test_add_job(self):
        stat = self.m.addJob(SucceedingJob)
        self.assert_(isinstance(stat, JobStatus))
        self.assert_(isinstance(stat.getJob(), Job))
        self.assert_(stat in self.m.jobs())

    def test_getUnfinishedJobs(self):
        status = self.m.addJob(SucceedingJob)
        self.assert_(status in self.m.getUnfinishedJobs())
        d = status.getJob().start()
        def _testFinishedness(r):
            self.assert_(status not in self.m.getUnfinishedJobs())
        d.addCallback(_testFinishedness)

    def _test_getRunningJobs(self):
        # FIXME: This test is broken because of reactor shiz.
        status = self.m.addJob(OneSecondJob)
        self.assert_(status not in self.m.getRunningJobs())
        d = status.getJob().start()
        # Yes, we're counting on a race condition for this test, but I don't
        # see any way around it without using Trial
        time.sleep(0.25)
        self.assert_(status in self.m.getRunningJobs())
        def _testFinishedness(r):
            self.assert_(status not in self.m.getRunningJobs())
        d.addCallback(_testFinishedness)

    def test_getPendingJobs(self):
        status = self.m.addJob(OneSecondJob)
        self.assert_(status in self.m.getPendingJobs())
        d = status.getJob().start()
        # Yes, we're counting on a race condition for this test, but I don't
        # see any way around it without using Trial
        time.sleep(0.25)
        self.assert_(status not in self.m.getPendingJobs())
        def _testFinishedness(r):
            self.assert_(status not in self.m.getPendingJobs())
        d.addCallback(_testFinishedness)


class TestLogFile(unittest.TestCase):
    def setUp(self):
        self.stat = JobStatus(Job('ajob'))
        self.log = self.stat.getLog()

    def test_create(self):
        self.assert_(isinstance(self.log, LogFile))
        self.assert_(self.log.getStatus() is self.stat)
        log2 = self.stat.getLog()
        self.assertEqual(self.log.getFilename(),
                         log2.getFilename())

    def test_write(self):
        data = ['foo', 'bar', 'spam', 'eggs']
        self.log.write(data[0])
        self.assertEqual(self.log.getText(), data[0])
        self.log.write(data[1])
        self.assertEqual(self.log.readlines(), ["".join(data[:2])])
        self.log.write("".join(data[2:]))
        self.assertEqual(self.log.readlines(), ["".join(data)])

class TestLogStream(unittest.TestCase):
    def setUp(self):
        self.stat = JobStatus(Job('ajob'))
        self.log = self.stat.getLog()
        self.stream = self.stat.getLog()

    def test_create(self):
        self.assertEqual(
            self.log.getFilename(),
            self.stream.getFilename()
        )
        self.assert_(self.stream.getFilename() is not None)

    def test_read(self):
        self.log.write('blah')
        data = self.stream.getText()
        self.assertEqual(data, 'blah')
        self.log.write('blah is a thingy')
        data = self.stream.getText()
        self.assertEqual(data, 'blahblah is a thingy')


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestJob))
    suite.addTest(makeSuite(TestJobStatus))
    suite.addTest(makeSuite(TestJobManager))
    suite.addTest(makeSuite(TestLogFile))
    suite.addTest(makeSuite(TestLogStream))
    return suite
