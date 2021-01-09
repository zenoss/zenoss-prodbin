##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os
import pkg_resources

try:
    VERSION = pkg_resources.get_distribution("Zenoss").version
except Exception:
    VERSION = "unknown"

BUILD_NUMBER = os.environ.get("BUILD_NUMBER", "DEV")
