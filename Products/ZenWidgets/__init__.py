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
#   Copyright (c) 2004 Zentinel Systems. All rights reserved.

"""__init__

Initializer for ZenTableManager

$Id: __init__.py,v 1.3 2004/04/04 23:56:49 edahl Exp $"""

__version__ = 0.5
__revision__ = "$Revision: 1.3 $"[11:-2]


from ZenTableManager import ZenTableManager
from ZenTableManager import manage_addZenTableManager

try:
    from Products.CMFCore.DirectoryView import registerDirectory
    registerDirectory('skins', globals())
except ImportError: pass

def initialize(registrar):
    registrar.registerClass(
        ZenTableManager,
        permission="Add ZenTableManager",
        constructors = (manage_addZenTableManager,),
        icon = "ZenTableManager_icon.gif"
    )
