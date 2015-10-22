##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


"""
Operations for support + support bundles.

Available at: /zport/dmd/support_router
"""
import logging
from Products import Zuul
from Products.ZenUtils.Ext import DirectRouter, DirectResponse

log = logging.getLogger('zen.SupportRouter')


class SupportRouter(DirectRouter):
    """
    A JSON/Ext.Direct interface to operations on support operations + bundles
    """
    def __init__(self, context, request):
        self.api = Zuul.getFacade('support', context.dmd)
        self.context = context
        self.request = request
        super(DirectRouter, self).__init__(context, request)

    def getBundlesInfo(self, page, uid, sort='moddate', dir='DESC', start=0, limit=50):
        results = self.api.getBundlesInfo(sort=sort, dir=dir, start=start, limit=limit)
        return DirectResponse(bundles=Zuul.marshal(results), totalCount=len(results))

    def createSupportBundle(self):
        data = self.api.createSupportBundle()
        return DirectResponse.succeed(new_jobs=Zuul.marshal(data))

    def deleteBundles(self, bundleNames):
        try:
            self.api.deleteSupportBundles(bundleNames)
            return DirectResponse.succeed('Successfully deleted all bundle(s)')
        except Exception as e:
            return DirectResponse.fail(e.message)

