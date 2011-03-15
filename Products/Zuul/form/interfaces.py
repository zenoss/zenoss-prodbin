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

from zope.interface import Interface

class IFormBuilder(Interface):
    """
    Builds the config for an Ext FormPanel based on the schema of the interface
    of the context.
    """
    def fields(fieldFilter=None):
        """
        Get the schema of the context and return the dictionary that will be
        used to render the form.
        @parameter fieldFilter: function to filter fields; return true to include, false to exclude. If none, all are included
        @type fieldFilter: function
        """
    def render():
        """
        Return the Ext config for the form.
        @parameter filter: funtion to filter fields; return true to include, false to exclude. If none, all are included
        @type filter: function
        """
