##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import logging
import os
import subprocess
from itertools import islice

from Products.Zuul.facades import ZuulFacade
from Products.Zuul.decorators import info
from Products.ZenUtils.Utils import supportBundlePath, binPath
from Products.Jobber.jobs import SubprocessJob


log = logging.getLogger('zen.SupportFacade')


class SupportFacade(ZuulFacade):

    @info
    def createSupportBundle(self):
        destpath = supportBundlePath()
        # make support bundle directory if it doesn't exist
        if not os.path.isdir(destpath):
            cmd = ['mkdir', '-p', destpath]
            retcode = subprocess.call(cmd)
            if retcode != 0:
                raise Exception("Failed to create support path")
        args = [binPath('zendiag.py')]
        jobStatus = self._dmd.JobManager.addJob(SubprocessJob,
                                                description="Create Support Bundle",
                                                kwargs=dict(cmd=args))
        return jobStatus

    @info
    def deleteSupportBundles(self, fileNames=()):
        """
        Delete the specified files from $ZENHOME/var/ext/support.
        Raises an exception if the support
        """
        supportDir = supportBundlePath()
        removed = []
        if os.path.isdir(supportDir):
            for dirPath, dirNames, dirFileNames in os.walk(supportDir):
                dirNames[:] = []
                for fileName in fileNames:
                    if fileName in dirFileNames:
                        os.remove(os.path.join(dirPath, fileName))
        else:
            """
            messaging.IMessageSender(self).sendToBrowser(
                'Support Bundle Directory Missing',
                'Unable to find $ZENHOME/var/ext/support.',
                messaging.WARNING
            )
            """
            raise Exception('Support bundle directory is missing')

    @info
    def getBundlesInfo(self, sort, dir, start, limit):
        start = max(start, 0)
        if limit is None:
            stop = None
        else:
            stop = start + limit
        bundles = self._dmd.getSupportBundleFilesInfo()
        # this only supports sorting by modDate, size, and fileName
        sortedBundles = sorted(bundles, key=lambda k: k[sort])
        if dir == 'DESC':
            return [ b for b in islice(reversed(sortedBundles), start, stop) ]
        return [ b for b in islice(sortedBundles, start, stop) ]


