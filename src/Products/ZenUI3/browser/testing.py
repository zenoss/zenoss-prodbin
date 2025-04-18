##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
import os
import logging
log = logging.getLogger('zen.UITests')
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ZopeTwoPageTemplateFile

from .javascript import getAllZenPackResources

log = logging.getLogger("zen.UITests")


class UserInterfaceTests(BrowserView):
    """
    Search through all the core javascript for tests files and send them back to the client
        to be evaluated.

        Any javascript file that starts with a "test" is considered a test file
    """
    __call__ = ZopeTwoPageTemplateFile("templates/userinterfacetests.pt")

    def getTestFiles(self):
        testFiles = self.getAllCoreJSTestFiles()
        for resource in getAllZenPackResources():
            testFiles.extend(self.getTestFilesFromResource(resource['name'], resource['directory']))
        return testFiles

    def getTestFilesFromResource(self, resource, path):
        tests = []
        resourcePath = "++resource++%s%s" % (
            resource,
            path.split("resources")[1],
        )
        for dirname, _, filenames in os.walk(path):
            for fn in filenames:
                fn = fn.lower()
                if fn.startswith("test") and fn.endswith(".js"):
                    testPath = os.path.join(dirname, fn)
                    tests.append(testPath.replace(path, resourcePath))
        return tests

    def getAllCoreJSTestFiles(self):
        path = os.path.join(
            os.path.dirname(__file__), "resources", "js", "zenoss"
        )
        resource = "zenui"
        test = self.getTestFilesFromResource(resource, path)
        log.info("Got the following tests %s", test)
        return test
