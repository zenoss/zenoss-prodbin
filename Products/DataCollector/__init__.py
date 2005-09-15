################################################################
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

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
