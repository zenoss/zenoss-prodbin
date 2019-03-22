##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import itertools

from mock import patch
from unittest import TestCase

from Products.Zuul.interfaces import IMarshallable

from ..interfaces import IJobRecord
from ..model import JobRecord
from ..storage import Fields
from .utils import subTest

UNEXPECTED = type("UNEXPECTED", (object,), {})()
PATH = {"src": "Products.Jobber.model"}


class JobRecordTest(TestCase):
    """Test the JobRecord class."""

    def setUp(t):
        t.data = {
            "jobid": "123",
            "name": "Products.Jobber.jobs.FooJob",
            "summary": "FooJob",
            "description": "A foo job",
            "userid": "zenoss",
            "logfile": "/opt/zenoss/log/jobs/123.log",
            "created": 1551804881.024517,
            "started": 1551804891.863857,
            "finished": 1551805270.154359,
            "status": "SUCCESS",
            "details": {
                "foo": "foo string",
                "bar": 123,
                "baz": 34597945.00234,
            },
        }

    def test_interfaces(t):
        for intf in (IJobRecord, IMarshallable):
            with subTest(interface=intf):
                t.assertTrue(intf.implementedBy(JobRecord))
                j = JobRecord.make({})
                t.assertTrue(intf.providedBy(j))

    def test_attributes(t):
        # Assert that JobRecord has all the attributes specified by Fields.
        j = JobRecord.make({})
        missing_names = set(Fields.viewkeys()) - set(dir(j))
        t.assertSetEqual(set(), missing_names)

    def test_make_badfield(t):
        with t.assertRaises(AttributeError):
            JobRecord.make({"foo": 1})

    def test_make(t):
        actual = JobRecord.make(t.data)
        expected = itertools.chain(
            t.data.items(),
            (
                ("complete", True),
                ("duration", t.data["finished"] - t.data["started"]),
            ),
        )
        for attribute, expected_value in expected:
            actual_value = getattr(actual, attribute, UNEXPECTED)
            with subTest(attribute=attribute):
                t.assertEqual(expected_value, actual_value)

    def test_complete(t):
        parameters = {
            ("PENDING", False),
            ("RETRY", False),
            ("RECEIVED", False),
            ("STARTED", False),
            ("REVOKED", True),
            ("ABORTED", True),
            ("FAILURE", True),
            ("SUCCESS", True),
        }
        record = JobRecord.make(t.data)
        for status, expected in parameters:
            with subTest(status=status):
                record.status = status
                t.assertEqual(
                    expected, record.complete, msg="status=%s" % status,
                )

    @patch("{src}.time".format(**PATH), autospec=True)
    def test_duration(t, time):
        current_tm = 1551804885.298103
        completed_duration = t.data["finished"] - t.data["started"]
        incomplete_duration = current_tm - t.data["started"]
        time.time.return_value = current_tm
        parameters = {
            ("PENDING", None),
            ("RETRY", incomplete_duration),
            ("RECEIVED", None),
            ("STARTED", incomplete_duration),
            ("REVOKED", completed_duration),
            ("ABORTED", completed_duration),
            ("FAILURE", completed_duration),
            ("SUCCESS", completed_duration),
        }
        record = JobRecord.make(t.data)
        for status, expected in parameters:
            with subTest(status=status):
                record.status = status
                t.assertEqual(expected, record.duration)
