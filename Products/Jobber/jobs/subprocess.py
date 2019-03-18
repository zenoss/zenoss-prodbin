##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging
import os
import socket
import subprocess
import time

from Products.ZenEvents import Event
from Products.ZenUtils.Utils import LineReader

from ..exceptions import SubprocessJobFailed, JobAborted
from .job import Job


class SubprocessJob(Job):
    """Use this job to execute shell commands."""

    name = "Products.Jobber.SubprocessJob"

    @classmethod
    def getJobType(cls):
        """Return a general, but brief, description of the job."""
        return "Shell Command"

    @classmethod
    def getJobDescription(cls, cmd, environ=None):
        """Return a description of the job."""
        return cmd if isinstance(cmd, basestring) else " ".join(cmd)

    def _run(self, cmd, environ=None):
        self.log.debug("Running Job %s %s", self.getJobType(), self.name)
        if environ is not None:
            try:
                newenviron = os.environ.copy()
                newenviron.update(environ)
                environ = newenviron
            except Exception:
                self.log.exception("environ is %s", environ)
                environ = None
        process = None
        exitcode = None
        output = ""
        handler = self.log.handlers[0]
        originalFormatter = handler.formatter
        lineFormatter = logging.Formatter("%(message)s")
        try:
            self.log.info(
                "Spawning subprocess: %s",
                SubprocessJob.getJobDescription(cmd),
            )
            process = subprocess.Popen(
                cmd,
                bufsize=1,
                env=environ,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )

            # Since process.stdout.readline() is a blocking call, it stops
            # the injected exception from being raised until it unblocks.
            # The LineReader object allows non-blocking readline()
            # behavior to avoid delaying the injected exception.
            reader = LineReader(process.stdout)
            reader.start()
            # Reset the log message formatter (restored later)
            while exitcode is None:
                line = reader.readline()
                if line:
                    try:
                        handler.setFormatter(lineFormatter)
                        self.log.info(line.strip())
                        output += line.strip()
                    finally:
                        handler.setFormatter(originalFormatter)
                else:
                    exitcode = process.poll()
                    time.sleep(0.1)
        except JobAborted:
            if process:
                self.log.warn("Job aborted. Killing subprocess...")
                process.kill()
                process.wait()  # clean up the <defunct> process
                self.log.info("Subprocess killed.")
            raise
        if exitcode != 0:
            device = socket.getfqdn()
            job_record = self.dmd.JobManager.getJob(self.request.id)
            description = job_record.job_description
            summary = 'Job "%s" finished with failure result.' % description
            message = "exit code %s for %s; %s" % (
                exitcode,
                SubprocessJob.getJobDescription(cmd),
                output,
            )

            self.dmd.ZenEventManager.sendEvent({
                "device": device,
                "severity": Event.Error,
                "component": "zenjobs",
                "eventClass": "/App/Job/Fail",
                "message": message,
                "summary": summary,
            })

            raise SubprocessJobFailed(exitcode)
        return exitcode
