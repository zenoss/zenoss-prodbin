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

import warnings
warnings.warn('Products.Device.StatusMonitorConf', DeprecationWarning)

__doc__="""StatusMonitorConf

The configuration object for monitors.

"""

from Products.ZenRelations.RelSchema import *

from Products.ZenModel.Monitor import Monitor
from Products.ZenModel.StatusColor import StatusColor


class StatusMonitorConf(Monitor, StatusColor):
    '''Configuration for monitors'''
    portal_type = meta_type = "StatusMonitorConf"

    monitorRootName = "StatusMonitors"

    _relations = (
        ("devices", ToMany(ToMany,"Products.ZenModel.Device","monitors")),
        )

