##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import math

from mock import call, MagicMock, mock_open, patch
from unittest import TestCase
from zope.component import getGlobalSiteManager, ComponentLookupError

from Products.Jobber.task.utils import (
    backoff,
    ConflictError,
    fibonacci,
    job_log_has_errors,
    ReadConflictError,
    transact,
)

from ..interfaces import IJobStore
from ..storage import JobStore
from .utils import RedisLayer

PATH = {"src": "Products.Jobber.task.utils"}


class JobLogHasErrorsTest(TestCase):
    """Test the task.utils.job_log_has_errors function.
    """

    layer = RedisLayer

    record = {
        "jobid": "123",
        "name": "TestJob",
        "summary": "Products.Jobber.jobs.TestJob",
        "description": "A test job",
        "userid": "zenoss",
        "logfile": "/opt/zenoss/log/jobs/123.log",
        "created": 1551804881.024517,
        "status": "PENDING",
    }

    def setUp(t):
        t.store = JobStore(t.layer.redis)
        t.store[t.record["jobid"]] = t.record
        getGlobalSiteManager().registerUtility(
            t.store, IJobStore, name="redis",
        )

    def tearDown(t):
        t.layer.redis.flushall()
        getGlobalSiteManager().unregisterUtility(
            t.store, IJobStore, name="redis",
        )
        del t.store

    def test_missing_jobstore(t):
        getGlobalSiteManager().unregisterUtility(
            t.store, IJobStore, name="redis",
        )
        with t.assertRaises(ComponentLookupError):
            job_log_has_errors("123")

    def test_undefined_logfile_name(t):
        t.store.update("123", logfile=None)
        t.assertFalse(job_log_has_errors("123"))

    def test_blank_logfile_name(t):
        t.store.update("123", logfile="")
        t.assertFalse(job_log_has_errors("123"))

    def test_bad_logfile(t):
        m = MagicMock(side_effect=RuntimeError("boom"))
        _open = mock_open(m)
        with patch("__builtin__.open", _open):
            t.assertFalse(job_log_has_errors("123"))

    def test_no_errors(t):
        _open = mock_open(read_data=(
            "INFO zen.zenjobs good things\n"
            "WARNING zen.zenjobs be alert\n"
            "DEBUG zen.zenjobs noisy things\n"
        ))
        with patch("__builtin__.open", _open):
            t.assertFalse(job_log_has_errors("123"))

    def test_has_errors(t):
        _open = mock_open(read_data=(
            "INFO zen.zenjobs good things\n"
            "ERROR zen.zenjobs bad things\n"
            "DEBUG zen.zenjobs noisy things\n"
        ))
        with patch("__builtin__.open", _open):
            t.assertTrue(job_log_has_errors("123"))


def is_perfect_square(n):
    s = int(math.sqrt(n))
    return (s * s) == n


def is_fibonacci(n):
    x = 5 * n * n
    return is_perfect_square(x + 4) or is_perfect_square(x - 4)


class FibonacciTest(TestCase):
    """Test the fibonacci generator function.
    """

    def test_correctness(t):
        limit = 10
        for i, n in enumerate(fibonacci(100)):
            if i >= limit:
                break
            t.assertTrue(is_fibonacci(n))

    def test_infiniteness(t):
        gen = fibonacci(30)
        iterations = 20
        repetitions = 0
        p, n = 0, next(gen)
        for i in range(iterations):
            if p == n:
                repetitions += 1
            p, n = n, next(gen)
        t.assertEqual(repetitions, 13)

    def test_limit_inexact(t):
        limit = 15
        gen = fibonacci(limit)
        samples = []
        for i in range(100):
            samples.append(next(gen))
        t.assertTrue(all(n <= limit for n in samples), samples)

    def test_limit_exact(t):
        limit = 34
        gen = fibonacci(limit)
        samples = []
        for i in range(100):
            samples.append(next(gen))
        t.assertTrue(all(n <= limit for n in samples), samples)


class BackoffWithFibonacciTest(TestCase):
    """Test the backoff function with the fibonacci generator.
    """

    def setUp(t):
        t.limit = 30
        gen = backoff(t.limit, fibonacci)
        t.samples = []
        for i in range(1000):
            t.samples.append(next(gen))

    def tearDown(t):
        del t.samples

    # A limit of 30 gives a median of 15.  Since we're using fibonacci
    # numbers, the median is actually 13 (highest number <= 15).

    def test_initial(t):
        expected = [1, 1, 2, 3, 5, 8, 13]
        actual = t.samples[:len(expected)]
        for e, a in zip(expected, actual):
            t.assertLessEqual(a, e * 2)
            t.assertGreaterEqual(a, e)

    def test_backoff_range(t):
        # All samples starting with offset 7 should be 13 <= x <= 26.
        offset = 7
        minimum = 13
        actual = t.samples[offset:]
        for a in actual:
            t.assertLessEqual(a, minimum * 2)
            t.assertGreaterEqual(a, minimum)

    def test_backoff_average(t):
        # The median value should be around 19.5 (<- 13 + 6.5)
        offset = 7
        subrange = t.samples[offset:]
        avg = math.fsum(subrange) / len(subrange)
        t.assertAlmostEqual(avg, 19.5, delta=0.5)

    def test_backoff_median(t):
        # The median value should be around 19.5 (<- 13 + 6.5)
        offset = 7
        subrange = t.samples[offset:]
        maxv = max(subrange)
        minv = min(subrange)
        median = math.fsum((maxv, minv)) / 2
        t.assertAlmostEqual(median, 19.5, places=1)


def _linear(limit):
    a = 0
    while True:
        if a < limit:
            a += 1
        yield a


class BackoffWithLinearTest(TestCase):
    """Test the backoff function with a linear number generator.
    """

    def setUp(t):
        gen = backoff(30, _linear)
        t.samples = []
        for i in range(1000):
            t.samples.append(next(gen))

    def tearDown(t):
        del t.samples

    # A limit of 30 means a max median of 15.

    def test_initial(t):
        expected = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
        actual = t.samples[:len(expected)]
        for e, a in zip(expected, actual):
            t.assertLessEqual(a, e * 2)
            t.assertGreaterEqual(a, e)

    def test_backoff_range(t):
        # All samples starting with offset 15 should be 15 <= x <= 30.
        offset = 15
        minimum = 15
        actual = t.samples[offset:]
        for a in actual:
            t.assertLessEqual(a, minimum * 2)
            t.assertGreaterEqual(a, minimum)

    def test_backoff_average(t):
        # The median value should be around 19.5 (<- 13 + 6.5)
        offset = 15
        subrange = t.samples[offset:]
        avg = math.fsum(subrange) / len(subrange)
        t.assertAlmostEqual(avg, 22.5, delta=0.5)

    def test_backoff_median(t):
        # The median value should be around 19.5 (<- 13 + 6.5)
        offset = 15
        subrange = t.samples[offset:]
        maxv = max(subrange)
        minv = min(subrange)
        median = math.fsum((maxv, minv)) / 2
        t.assertAlmostEqual(median, 22.5, places=1)


class TransactTest(TestCase):
    """Test the transact decorator.
    """

    def test_nominal_no_args(t):
        expected = (10, 1)

        def func():
            return expected

        b = MagicMock()
        s = MagicMock()
        c = MagicMock()
        retries = 5
        tx = transact(func, retries, b, sleep=s, ctx=c)
        actual = tx()
        t.assertSequenceEqual(expected, actual)
        c.commit.assert_called_once_with()
        c.abort.assert_not_called()

    def test_nominal_with_args(t):
        args = (10,)
        kw = {"a": 1}

        def func(arg, a=None):
            return arg, a

        expected = (10, 1)

        b = MagicMock()
        s = MagicMock()
        c = MagicMock()
        retries = 5
        tx = transact(func, retries, b, sleep=s, ctx=c)
        actual = tx(*args, **kw)
        t.assertSequenceEqual(expected, actual)
        c.commit.assert_called_once_with()
        c.abort.assert_not_called()

    def test_readconflict(t):
        def func():
            raise ReadConflictError()

        delays = list(range(1, 10))

        def b():
            for i in delays:
                yield i

        bgen = b()
        s = MagicMock()
        c = MagicMock()
        retries = 5
        tx = transact(func, retries, bgen, sleep=s, ctx=c)

        with t.assertRaises(ReadConflictError):
            tx()

        c.commit.assert_not_called()
        abort_calls = [call() for _ in range(retries)]
        c.abort.assert_has_calls(abort_calls, any_order=True)
        t.assertEqual(c.abort.call_count, retries)

        # Only four calls to wait(); there is no wait after the final attempt.
        wait_calls = [call(v) for v in delays[:retries - 1]]
        s.wait.assert_has_calls(wait_calls, any_order=True)
        t.assertEqual(s.wait.call_count, retries - 1)

    def test_conflict(t):
        def func():
            pass

        delays = list(range(1, 10))

        def b():
            for i in delays:
                yield i

        bgen = b()
        s = MagicMock()
        c = MagicMock()
        c.commit.side_effect = ConflictError()
        retries = 5
        tx = transact(func, retries, bgen, sleep=s, ctx=c)

        with t.assertRaises(ConflictError):
            tx()

        commit_calls = [call() for _ in range(retries)]
        c.commit.assert_has_calls(commit_calls, any_order=True)
        t.assertEqual(c.commit.call_count, retries)

        abort_calls = [call() for _ in range(retries)]
        c.abort.assert_has_calls(abort_calls, any_order=True)
        t.assertEqual(c.abort.call_count, retries)

        # Only four calls to wait(); there is no wait after the final attempt.
        wait_calls = [call(v) for v in delays[:retries - 1]]
        s.wait.assert_has_calls(wait_calls, any_order=True)
        t.assertEqual(s.wait.call_count, retries - 1)

    def test_resolves_conflict(t):
        def func():
            pass

        delays = list(range(1, 10))

        def b():
            for i in delays:
                yield i

        def effect(data):
            def effecter():
                if data.count < 2:
                    data.count += 1
                    raise ConflictError()
            return effecter

        bgen = b()
        s = MagicMock()

        data = type("data", (object,), {"count": 0})()
        c = MagicMock()
        c.commit.side_effect = effect(data)
        retries = 5
        tx = transact(func, retries, bgen, sleep=s, ctx=c)
        tx()

        commit_calls = [call(), call(), call()]
        c.commit.assert_has_calls(commit_calls, any_order=True)
        t.assertEqual(c.commit.call_count, 3)

        # Abort call count is one less than the commit call count.
        abort_calls = [call(), call()]
        c.abort.assert_has_calls(abort_calls, any_order=True)
        t.assertEqual(c.abort.call_count, 2)

        # The number of wait calls should match the number of abort calls.
        wait_calls = [call(v) for v in delays[:len(abort_calls)]]
        s.wait.assert_has_calls(wait_calls, any_order=True)
        t.assertEqual(s.wait.call_count, 2)
