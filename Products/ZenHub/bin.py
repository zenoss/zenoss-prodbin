##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import argparse

import Products.ZenHub as ZENHUB_MODULE

from Products.ZenCollector.configcache.app.args import (
    get_arg_parser,
    get_subparser,
)
from Products.ZenCollector.configcache.app.genconf import GenerateConfig
from Products.ZenUtils.config import (
    add_config_arguments,
    getConfigFromArguments,
)
from Products.ZenUtils.init import initialize_environment
from Products.ZenUtils.logger import (
    add_logging_arguments,
    setup_logging_from_dict,
    install_debug_logging_signal,
)
from Products.ZenUtils.pidfile import add_pidfile_arguments
from Products.ZenUtils.zodb import add_zodb_arguments

from . import PB_PORT
from .localserver import (
    LocalServer,
)


def zenhubworker():
    """
    Main entrypoint for the zenhubworker application.
    """
    parser = get_arg_parser("ZenHubWorker Commands and Options")
    subparsers = parser.add_subparsers(title="Commands")

    GenerateConfig.add_command(subparsers, parser)
    _ZenHubWorkerRunCommand.add_command(parser, subparsers)

    args = parser.parse_args()
    args.factory(args).run()


class _ZenHubWorkerRunCommand(object):

    description = "Run the ZenHubWorker"

    @staticmethod
    def add_command(parser, subparsers):
        subp_run = get_subparser(
            subparsers, "run", _ZenHubWorkerRunCommand.description
        )
        add_config_arguments(parser, parser.prog)
        add_logging_arguments(subp_run, parser.prog)
        add_zodb_arguments(subp_run)
        add_pidfile_arguments(subp_run, parser.prog)
        LocalServer.add_arguments(subp_run)
        _add_zenhubworker_arguments(subp_run)
        subp_run.set_defaults(
            factory=_ZenHubWorkerRunCommand,
            parser=subp_run,
        )

    def __init__(self, args):
        self.args = args

    def run(self):
        config = getConfigFromArguments(self.args.parser, self.args)
        initialize_environment(configs=(("hubworker.zcml", ZENHUB_MODULE),))
        setup_logging_from_dict(config)
        install_debug_logging_signal(config["log-level"])


def _add_zenhubworker_arguments(parser):
    parser.add_argument(
        "--hubhost",
        default="localhost",
        help="Host to use for connecting to ZenHub",
    )
    parser.add_argument(
        "--hubport",
        type=int,
        default=PB_PORT,
        help="Port to use for connecting to ZenHub",
    )
    parser.add_argument(
        "--hubusername",
        default="admin",
        help="Login name to use when connecting to ZenHub",
    )
    parser.add_argument(
        "--hubpassword",
        default="zenoss",
        help="password to use when connecting to ZenHub",
    )
    parser.add_argument(
        "--hub-response-timeout",
        default=30,
        type=int,
        help="ZenHub response timeout interval (in seconds)",
    )
    parser.add_argument(
        "--call-limit",
        type=int,
        default=200,
        help="Maximum number of remote calls before restarting worker",
    )
    parser.add_argument(
        "--profiling",
        action="store_true",
        default=False,
        help="Run with profiling on",
    )
    parser.add_argument(
        "--monitor",
        default="localhost",
        help="Name of the performance monitor this hub runs on",
    )
    parser.add_argument(
        "--workerid",
        type=int,
        default=0,
        help=argparse.SUPPRESS,
    )
