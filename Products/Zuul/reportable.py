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

from zope.interface import implements
from zope.component import adapts
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.Zuul.interfaces import IReportable

import re

class BaseReportable(object):
    implements(IReportable)
    adapts(ZenModelRM)

    def __init__(self, context):
        super(BaseReportable, self).__init__()
        self.context = context
        
    @property
    def id(self):
        return self.context.id

    @property
    def uid(self):
        _uid = getattr(self, '_v_uid', None)
        if _uid is None:
            _uid = self._v_uid = '/'.join(self.context.getPrimaryPath())
        return _uid

    @property
    def entity_class_name(self):
        _meta_type = getattr(self, '_v_meta_type', None)
        if _meta_type is None:
            ccre = re.compile('(?<=[a-z])(?=[A-Z])')
            meta_type = self.context.meta_type
            _meta_type = self._v_meta_type = ccre.sub('_', meta_type).lower()
        return _meta_type

    @property
    def exportable(self):
        return True

    def reportProperties(self):
        'property name, type, value'
        return [self._getProperty(prop) for prop in self.context._properties]

    def _getProperty(self, property):
        propId = property['id']
        propType = property['type']

        if propType == 'keyedselection':
            select_variable = eval('self.context.' + property['select_variable'] + '()')
            value = eval('self.context.' + propId)
            for var in select_variable:
                if var[1] == value:
                      return (propId, 'string', var[0])
            return (propId, 'string', '')
        elif propType == 'selection':
            selection = eval('self.context.' + propId)
            return (propId, 'string', '' if not selection else selection)
        elif propType == 'text':
            return (propId, 'string', eval('self.context.' + propId))
        elif propType == 'lines':
            value = eval('self.context.' + propId)
            return (propId, propType, '\n'.join([str(item) for item in value]))
        elif propType in ['int', 'long', 'string', 'boolean', 'date', 'float']:
            return (propId, propType, eval('self.context.' + propId))
        else:
            print 'not expecting propType:', propType
            return (propId, 'string', str(eval('self.context.' + propId)))

