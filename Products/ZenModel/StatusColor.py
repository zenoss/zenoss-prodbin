#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

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
