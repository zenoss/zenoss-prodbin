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

__doc__="""Status

StatusColor class is a base for things which have status
that needs to be represented in html with color.

$Id: StatusColor.py,v 1.8 2004/04/04 01:51:19 edahl Exp $"""

__version__ = "$Revision: 1.8 $"[11:-2]

class StatusColor:
    """Status object"""

    def devStatusColor(self, status):
        retval="#00ff00"
        if status == -1:
            retval = "#d02090"
        elif status == -2:
            retval = "#ff9900"
        elif status > 0:
            retval = "#ff0000"
        return retval

    def pingColor(self):
        return self.statusColor(self.pingStatus)

    def snmpColor(self):
        return self.statusColor(self.snmpStatus)
