#! /usr/bin/env python 
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

__doc__="""
ZenDeleteHistory
"""

from ZenScriptBase import ZenScriptBase


class ZenDeleteHistory(ZenScriptBase):
    """
    Delete events from the history table
    """

    def buildOptions(self):
        """
        Setup the command line options
        """
        self.parser.add_option('-n', '--numDays',
                    dest='numDays', default=None,
                    help='Number of days of history to keep')
        self.parser.add_option('-d', '--device',
                    dest='device', default=None,
                    help='Devide id for which to delete events')
        ZenScriptBase.buildOptions(self)


    def deleteHistory(self):
        """
        Delete historical events.  If device is given then only delete
        events for that device.  If numDays is given then only delete
        events that are older than that many days.
        device and numDays are mutually exclusive.  No real reason for this
        other than there is no current need to use both in same call and I
        don't want to test the combination.
        """
        if self.options.numDays:
            try:
                self.options.numDays = int(self.options.numDays)
            except ValueError:
                raise ValueError('numDays argument must be an integer')
        
        self.connect()
        
        if self.options.device:
            statement = 'delete from history '
            whereClause = 'where device = "%s"' % self.options.device
            reason = 'Deleting events for device %s' % self.options.device
            toLog = True
        elif self.options.numDays > 0:
            statement = ('delete h,j,d from history h '
                'LEFT JOIN log j ON h.evid = j.evid '
                'LEFT JOIN detail d ON h.evid = d.evid ')
            whereClause = ('WHERE StateChange < DATE_SUB(NOW(), '
                            'INTERVAL %s day)' % self.options.numDays)
            reason = ''
            toLog = False
        else:
            return
        print '%s%s' % (statement, whereClause)
        self.dmd.ZenEventManager.updateEvents(statement, whereClause, reason,
                                                toLog=toLog, table='history')

if __name__ == '__main__':
    ZenDeleteHistory().deleteHistory()
