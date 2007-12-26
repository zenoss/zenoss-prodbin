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

__doc__="""BuiltInDS

Define a data source for RRD files that just appear without
additional configuration.
"""

from Globals import InitializeClass
from RRDDataSource import RRDDataSource

class BuiltInDS(RRDDataSource):

    sourcetypes = ('Built-In',)
    sourcetype = 'Built-In'
    
InitializeClass(BuiltInDS)
    
