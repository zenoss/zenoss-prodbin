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

"""__init__

Initializer for netcool connector product

$Id: __init__.py,v 1.2 2003/10/01 20:56:37 edahl Exp $"""

__version__ = "$Revision: 1.2 $"[11:-2]

from Products.CMFCore.DirectoryView import registerDirectory

#from DataCollector import DataCollector, manage_addDataCollector

# Make the data maps available as DirectoryViews.
#registerDirectory('maps', globals())


def initialize(registrar):
    pass
#    registrar.registerClass(
#        DataCollector,
#        constructors = (manage_addDataCollector,),)
