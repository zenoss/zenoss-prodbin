##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import json
import time
from Products.Five.browser import BrowserView

class Login(BrowserView):
    """
    """

    def __call__(self, *args, **kwargs):
        """
        """
        return json.dumps(dict(id="123456", expires=time.time()))

class Validate(BrowserView):
    """
    """

    def __call__(self, *args, **kwargs):
        """
        """
        return json.dumps(dict(id="123456", expires=time.time()))
