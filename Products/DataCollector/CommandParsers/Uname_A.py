##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


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
