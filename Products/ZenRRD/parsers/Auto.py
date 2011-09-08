###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Products.ZenRRD.parsers.Cacti import Cacti
from Products.ZenRRD.parsers.Nagios import Nagios
from Products.ZenRRD.CommandParser import CommandParser, ParsedResults

class Auto(CommandParser):


    def processResults(self, cmd, result):

        # best effort.  Try Nagios first, if that doesn't return data values
        # try Cacti. If cacti doesn't return value use results from nagios
        # since it is more likely to have been an error parsing nagios data
        # and the nagios parser puts more data in the event.  Both parsers
        # have the same logic for event severity based on exit code

        cactiResult= None
        nagiosResult = ParsedResults()

        nagiosParser = Nagios()
        nagiosParser.processResults(cmd, nagiosResult)

        if not nagiosResult.values:
            cactiParser = Cacti()
            cactiResult= ParsedResults()
            cactiParser.processResults(cmd, cactiResult)

        if cactiResult and cactiResult.values:
           #use cacti results
            parserResult = cactiResult
        else:
            parserResult = nagiosResult

        result.events.extend(parserResult.events)
        result.values.extend(parserResult.values)

