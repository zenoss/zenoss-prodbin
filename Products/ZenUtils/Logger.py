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

"""Logger

Log messages from all confmon applications.  Logger
will use the new python loggin stuff to route log
nad filter messages.  This is also where
lookups of error message translations happens.


$Id: Logger.py,v 1.3 2002/07/19 17:02:41 edahl Exp $"""

__version__ = "$Revision: 1.3 $"[11:-2]

import time

FATAL = 5
CRITICAL = 4
WARNING = 3
INFORMATION = 2
DEBUG = 1

severities = (
            "NONE", 
            "DEBUG", 
            "WARNING", 
            "CRITICAL", 
            "FATAL"
            )

def logger(level, message):
    """logger(level, message) -> log message with levl and time"""
    print time.asctime() + " " + severities[level] + ": " + message
