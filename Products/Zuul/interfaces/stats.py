###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
from zope.interface import Attribute, Interface

class ISystemMetric(Interface):
    category = Attribute("Category of the system static, eg Zope")

    def metrics():
        """
        A dictionary of metrics. A metric is either a number or a dict with a
        "value" key.
        """

