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

from Products.Zuul.interfaces import IInfo
from Products.Zuul.form import schema
from Products.Zuul.utils import ZuulMessageFactory as _t


class IGraphPointInfo(IInfo):
    """
    Adapts GraphPoint.
    """
    newId = schema.Text(title=_t(u'Name'),
                       required=True,
                       order=1)
    type = schema.Text(title=_t(u'Type'),
                       readonly=True,
                       order=2)
    # this should always appear last (hence the 999)
    rrdVariables = schema.Text(title=_t(u'Available RRD Variables'),
                               order=999,
                               xtype='multilinedisplayfield')


class IColorGraphPointInfo(IGraphPointInfo):
    """
    Abstract interface for every graph point that has a color field
    """
    color = schema.Text(title=_t('Color (Hex value RRGGBB)'),
                        vtype='hexnumber')
    legend = schema.Text(title=_t('Legend'))


class IThresholdGraphPointInfo(IColorGraphPointInfo):
    """
    Adapts Threshold Graph Point Info
    """


class IDataPointGraphPointInfo(IColorGraphPointInfo):
    """
    Adapts DataPoint GraphPoint.
    """
    lineType = schema.Choice(title=_t('Line Type'),
                             vocabulary='complexGraphLineType',
                             order=5)
    lineWidth = schema.Text(title=_t('Line Width'), order=6)
    stacked = schema.Bool(title=_t('Stacked'), order=7)
    format = schema.Text(title=_t('Format'), order=8)
    dpName = schema.Text(title=_t('DataPoint'), readonly=True, order=3)
    rpn = schema.TextLine(title=_t('RPN'), order=10)
    limit = schema.Int(title=_t('Limit'), order=11)
    cFunc = schema.Text(title=_t('Consolidation'), order=12)


class IDefGraphPointInfo(IGraphPointInfo):
    """
    Adapts Def Graph Points
    """
    rrdFile = schema.Text(title=_t(u'RRD File'))
    dsName = schema.Text(title=_t(u'RRD Data Source'))
    cFunc = schema.Text(title=_t(u'Consolidation'))
    start = schema.Text(title=_t(u'Start'))
    end = schema.Text(title=_t(u'End'))
    step = schema.Text(title=_t(u'Step'))
    rFunc = schema.Text(title=_t(u'Reduce'))


class IVdefGraphPointInfo(IGraphPointInfo):
    """
    Adapts Vdef Graph Points
    """
    rpn = schema.TextLine(title=_t(u'RPN'))


class IPrintGraphPointInfo(IGraphPointInfo):
    """
    Adapts Print Graph Points
    """
    vname = schema.Text(title=_t(u'Vname'))
    format = schema.Text(title=_t(u'Format'))
    strftime = schema.Text(title=_t(u'Strftime'))


class ICommentGraphPointInfo(IGraphPointInfo):
    """
    Adapts Print Graph Points
    """
    text = schema.Text(title=_t(u'Text'))


class IVruleGraphPointInfo(IColorGraphPointInfo):
    """
    Adapts VRule Graph Points
    """
    time = schema.Int(title=_t(u'Time'),
                      vtype='positive')


class IHruleGraphPointInfo(IColorGraphPointInfo):
    """
    Adapts HRule Graph Points
    """
    value = schema.Text(title=_t(u'Value'))


class ILineGraphPointInfo(IColorGraphPointInfo):
    """
    Adapts Line Graph Points
    """
    lineWidth = schema.Int(title=_t(u'Line Width'))
    stacked = schema.Bool(title=_t('Stacked'))
    value = schema.Text(title=_t(u'Value'))


class IAreaGraphPointInfo(IColorGraphPointInfo):
    """
    Adapts HRule Graph Points
    """
    stacked = schema.Bool(title=_t('Stacked'))
    value = schema.Text(title=_t(u'Value'))


class ITickGraphPointInfo(IColorGraphPointInfo):
    """
    Adapts Tick Graph Points
    """
    vname = schema.Text(title=_t(u'Vname'))
    fraction = schema.Text(title=_t(u'Fraction'))


class IShiftGraphPointInfo(IGraphPointInfo):
    """
    Adapts Shift Graph Points
    """
    vname = schema.Text(title=_t(u'Vname'))
    offset = schema.Int(title=_t(u'Offset'))
