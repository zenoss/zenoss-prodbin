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

__doc__ = """CommandParser

CommandParser parses the output of a command to return a datamap

$Id: Uname_A.py,v 1.2 2003/10/01 23:40:51 edahl Exp $"""

__version__ = '$Revision: 1.2 $'[11:-2]

from CommandParser import CommandParser

class Uname_A(CommandParser):
    
    command = 'uname -a'

    def condition(self, device, log):
        return "Servers" in device.getPrimaryPath()

    def parse(self, device, results, log):
        om = self.newObjectMap()
        om['comments'] = results.strip()
        return om

    def description(self):
        return "get uname -a from server and put in description"
