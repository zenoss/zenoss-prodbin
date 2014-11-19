#!/usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from twisted.spread import pb
from twisted.internet import reactor
import sys
import argparse

result = 0


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description=(
        'Health check for PerspectiveBroker. Return is 0 '
        'for healthy, 1 otherwise.'))
    parser.add_argument('--port', '-P', default=8789, help='port to test',
                        type=int)
    parser.add_argument('--host', '-H', default='127.0.0.1',
                        help='host to test')
    args = parser.parse_args()
    return args


def main():
    """Try to initiate pb connection to host, return status accordingly."""
    args = parse_arguments()
    factory = pb.PBClientFactory()
    reactor.connectTCP(args.host, args.port, factory)
    def1 = factory.getRootObject()
    def1.addCallbacks(handler, err_handler)
    reactor.run()
    sys.exit(result)


def handler(_):
    """Handle successful retrieval of root object."""
    global result
    reactor.stop()
    result = 0


def err_handler(_):
    """Handle failure to retrieve root object."""
    global result
    result = 1
    reactor.stop()


if __name__ == '__main__':
    main()
