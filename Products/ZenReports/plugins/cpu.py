###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2009 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import Globals
from Products.ZenReports.AliasPlugin import AliasPlugin

class cpu( AliasPlugin ):
    """
    The cpu usage report
    """

    def getAliasColumnMap(self):
        ##      alias/dp id : column name
        return {'loadAverage5min':'laLoadInt5', 
                'cpu__pct':'cpuPercent'}


    
