##############################################################################
#
# Copyright (C) Zenoss, Inc. 2025, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import


class UnknownServiceError(RuntimeError):
    """Raised when an unknown configuration service is requested."""
