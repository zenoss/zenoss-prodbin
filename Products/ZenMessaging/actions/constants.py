###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

class ActionTargetType(object):
    """Helper to hold action target types."""

    Unknown     = 'Unknown'     # use sparingly, for unexpected values.
    ManualEntry = 'ManualEntry'

    # users
    User        = 'User'
    Group       = 'Group'
    Role        = 'Role'

    # devices
    Class       = 'Class'
    Organizer   = 'Organizer'
    Device      = 'Device'
    Component   = 'Component'
    Location    = 'Location'
    zProperty   = 'zProperty'

    # templates
    Template    = 'Template'
    DataSource  = 'RRDDataSource'
    DataPoint   = 'RRDDataPoint'
    Graph       = 'Graph'
    GraphPoint  = 'GraphPoint'
    GraphDefinition = 'GraphDefinition'
    Threshold   = 'ThresholdClass'

    # other
    Hub         = 'Hub'
    Collector   = 'Collector'
    Dashboard   = 'Dashboard'
    ZenPack     = 'ZenPack'
    Mib         = 'MIB'
    Process     = 'Process'
    Report      = 'Report'
    Service     = 'Service'
    Network     = 'Network'
    Trigger     = 'Trigger'
    Notification        = 'Notification'
    NotificationWindow  = 'NotificationWindow'


class ActionName(object):
    """Holds common action names."""

    # Use whatever terminology the code does.
    Create  = 'Create'
    Add     = 'Add'
    Rename  = 'Rename'
    Edit    = 'Edit'
    Move    = 'Move'
    Remove  = 'Remove'
    Delete  = 'Delete'
