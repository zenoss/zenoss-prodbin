###########################################################################
#       
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#       
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#       
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from manager import SecondaryNavigationManager

def getSelectedNames(view):
    mgr = SecondaryNavigationManager(view.context, view.request, view)
    mgr.update()
    primary = mgr.getActivePrimaryName()
    for v in mgr.getActiveViewlets():
        if v.selected:
            secondary = v.__name__
            break
    else:
        secondary = ''
    return primary, secondary

