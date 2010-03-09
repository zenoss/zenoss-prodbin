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

from Products.Zuul.interfaces.info import IInfo

class ITemplateNode(IInfo):
    """
    A template node contains template leaves. It contains all of the templates
    throughout device class hierarchy that share the same id.
    """

class ITemplateLeaf(IInfo):
    """
    A template leaf is a single instance of an RRD template at a specific
    spot in the device class hierarchy.
    """

class IDataSourceInfo(IInfo):
    """
    Adapts RRDDataSource.
    """

class IDataPointInfo(IInfo):
    """
    Adapts RRDDataPoint.
    """

class IThresholdInfo(IInfo):
    """
    Adapts ThresholdClass.
    """

class IMinMaxThresholdInfo(IThresholdInfo):
    """
    Adapts the MinMaxThresholdClass
    """
    
class IGraphInfo(IInfo):
    """
    Adapts GraphDefinition.
    """
