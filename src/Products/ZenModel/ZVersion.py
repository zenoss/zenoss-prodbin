##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os


def _load_version():
    import importlib_metadata as metadata
    import pkg_resources

    version_str = metadata.version("zenoss")
    version = pkg_resources.parse_version(version_str)
    return version.base_version


VERSION = _load_version()
BUILD_NUMBER = os.environ.get("BUILD_NUMBER", "DEV")
