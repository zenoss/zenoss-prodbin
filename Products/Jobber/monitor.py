##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

# import ast

from celery.bin.base import Command
from collections import defaultdict
from datetime import timedelta
from zope.component import getUtility

from .interfaces import IJobStore
from .utils.datetime import humanize_timedelta


def catch_error(f):
    # Decorator that catches and prints the exception thrown from the
    # decorated function.
    def call_func(*args, **kw):
        try:
            return f(*args, **kw)
        except Exception as ex:
            print(ex)

    return call_func


class ZenJobsMonitor(Command):
    """Monitor Celery events."""

    @catch_error
    def task_failed(self, event):
        self.state.event(event)
        jobid = event["uuid"]
        instance = self.state.tasks.get(jobid)
        job = self.app.tasks.get(instance.name)
        result = job.AsyncResult(jobid)
        classkey, summary = _getErrorInfo(self.app, result.result)
        # args = ast.literal_eval(instance.args)
        # kwargs = ast.literal_eval(instance.kwargs)
        name = job.getJobType() if hasattr(job, "getJobType") else job.name
        print(
            "Job failed  worker=%s jobid=%s name=%s" % (
                event["hostname"], jobid, name,
            )
        )

    def run(self, **kw):
        self.state = self.app.events.State(
            on_node_join=on_node_join,
            on_node_leave=on_node_leave,
        )
        self.seconds_since = defaultdict(float)
        self.storage = getUtility(IJobStore, "redis")

        conn = self.app.connection().clone()

        def _error_handler(exc, interval):
            print("Internal error: %s" % (exc,))

        while True:
            print("Begin monitoring for zenjobs/celery events")
            try:
                conn.ensure_connection(_error_handler)
                recv = self.app.events.Receiver(
                    conn,
                    handlers={
                        "task-failed": self.task_failed,
                        "*": self.state.event,
                    },
                )
                recv.capture(wakeup=True)
            except (KeyboardInterrupt, SystemExit):
                return conn and conn.close()
            except conn.connection_errors + conn.channel_errors:
                print("Connection lost, attempting reconnect")


def _getTimeoutSummary(app, ex):
    return "Job killed after {}.".format(
        humanize_timedelta(
            timedelta(
                seconds=app.conf.get("CELERYD_TASK_SOFT_TIME_LIMIT"),
            ),
        ),
    )


def _getAbortedSummary(app, ex):
    return "Job aborted by user"


def _getErrorSummary(app, ex):
    return "{0.__class__.__name__}: {0}".format(ex)


_error_eventkey_map = {
    "TaskAborted": (
        "zenjobs-aborted", _getAbortedSummary,
    ),
    "SoftTimeLimitExceeded": (
        "zenjobs-timeout", _getTimeoutSummary,
    )
}


def _getErrorInfo(app, ex):
    """Returns (eventkey, summary).
    """
    key, summary_fn = _error_eventkey_map.get(
        type(ex).__name__, ("zenjobs-failure", _getErrorSummary),
    )
    return key, summary_fn(app, ex)


def on_node_join(*args, **kw):
    worker = args[0]
    print(
        "Worker node added to monitor  worker=%s uptime=%s" % (
            worker.hostname,
            humanize_timedelta(timedelta(seconds=worker.clock)),
        ),
    )


def on_node_leave(*args, **kw):
    worker = args[0]
    print(
        "Worker node left monitor  worker=%s uptime=%s" % (
            worker.hostname,
            humanize_timedelta(timedelta(seconds=worker.clock)),
        ),
    )
