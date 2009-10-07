###########################################################################
#       
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#       
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#       
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import zope.interface

class IEventManagerProxy(zope.interface.Interface):
    """
    Holds several methods useful for interacting with a Zenoss event manager.
    """
    def _is_history():
        """
        Should we be dealing with a history manager?
        """
    def _evmgr():
        """
        Get an event manager
        """
    def _extract_data_from_zevent():
        """
        Turn an event into a dictionary containing necessary fields.
        """


class IEventConsoleInitialData(zope.interface.Interface):
    """
    Marker interface for event console JavaScript snippets defining initial
    data to be rendered by the grid.
    """
