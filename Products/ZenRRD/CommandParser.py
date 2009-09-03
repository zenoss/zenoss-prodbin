###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import logging
log = logging.getLogger('zen.ZenRRD.CommandParser')

from pprint import pformat

class ParsedResults:

    def __init__(self):
        self.events = []                # list of event dictionaries
        self.values = []                # list of (DataPointConfig, value)
        
    def __repr__(self):
        args = (pformat(self.events), pformat(self.values))
        return "ParsedResults\n  events: %s\n  values: %s}" % args

class CommandParser:

    def dataForParser(self, context, datapoint):
        return {}

    def processResults(self, cmd, results):
        """
        Process the results of a running a command.

        @type cmd: Products.ZenRRD.zencommand.Cmd

        @param cmd: the results of running a command, with the
        configuration from ZenHub
        @param results: the values and events from the command output
        @return: None.
        """
        raise NotImplementedError
