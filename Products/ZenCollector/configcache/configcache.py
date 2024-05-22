##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

from .app.args import get_arg_parser
from .cli import Expire, List_, Remove, Show, Stats
from .invalidator import Invalidator
from .manager import Manager
from .version import Version


def main(argv=None):
    parser = get_arg_parser("configcache commands")

    subparsers = parser.add_subparsers(title="Commands")

    Version.add_arguments(parser, subparsers)
    Manager.add_arguments(parser, subparsers)
    Invalidator.add_arguments(parser, subparsers)
    Expire.add_arguments(parser, subparsers)
    List_.add_arguments(parser, subparsers)
    Remove.add_arguments(parser, subparsers)
    Show.add_arguments(parser, subparsers)
    Stats.add_arguments(parser, subparsers)

    args = parser.parse_args()
    args.factory(args).run()
