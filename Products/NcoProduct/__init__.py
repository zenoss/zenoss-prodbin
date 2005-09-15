################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

"""__init__

Initializer for netcool connector product

$Id: __init__.py,v 1.8 2004/04/22 19:08:47 edahl Exp $"""

__version__ = "$Revision: 1.8 $"[11:-2]

from Products.CMFCore.DirectoryView import registerDirectory

from NcoManager import NcoManager, manage_addNcoManager
from DmdNcoManager import DmdNcoManager, manage_addDmdNcoManager

registerDirectory('skins', globals())

def initialize(registrar):
    registrar.registerClass(
        NcoManager,
        constructors = (manage_addNcoManager,)
        )
    registrar.registerClass(
        DmdNcoManager,
        constructors = (manage_addDmdNcoManager,)
        )
