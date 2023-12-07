##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from .misc import app_name
from .misc.args import get_subparser


class Version(object):

    description = "Display the version and exit"

    @staticmethod
    def add_arguments(parser, subparsers):
        subp_version = get_subparser(
            subparsers, "version", Version.description
        )
        subp_version.set_defaults(factory=Version)

    def __init__(self, args):
        pass

    def run(self):
        from Products.ZenModel.ZenossInfo import ZenossInfo

        zinfo = ZenossInfo("")
        version = zinfo.getZenossVersion().short()
        print("{} {}".format(app_name(), version))
