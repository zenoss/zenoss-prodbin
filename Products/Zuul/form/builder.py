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

import operator
import zope.schema
from zope.component import adapts
from zope.interface import implements, providedBy
from zope.schema.vocabulary import getVocabularyRegistry
from zope.schema.vocabulary import VocabularyRegistryError
from Products.Zuul.form.interfaces import IFormBuilder
from Products.Zuul.interfaces import IInfo

ordergetter = operator.itemgetter('order')

FIELDKEYS = (
    'xtype',
    'title',
    'description',
    'readonly',
    'order',
    'group',
    'decimalPrecision',
    'vtype'
)


def _dict(field):
    """
    Turns a zope.schema.Field into a dictionary with our desired keys.
    """
    return dict((k, getattr(field, k, None)) for k in FIELDKEYS)


def _fieldset(name, items):
    """
    Turns a list into a fieldset config.
    """
    return {
        'xtype': 'fieldset',
        'title': name,
        'items': map(_item, items)
    }


def _item(item):
    """
    Turns a dict representing a field into a config.
    """
    if item['readonly']:
        if item['xtype']=='checkbox':
            xtype = 'checkbox'
            item['disabled'] = True
        elif item['xtype']=='linkfield':
            xtype = 'linkfield'
        else:
            xtype = 'displayfield'
    else:
        xtype = item['xtype']
    value = item['value']
    if xtype == 'linkfield':
        value = getattr(value, 'uid', value)
    field = {
        'xtype': xtype,
        'fieldLabel': item['title'],
        'name': item['name'],
        'value': value,
        'vtype': item['vtype']
    }
    if xtype == 'numberfield':
        field['decimalPrecision'] = item['decimalPrecision']
    if xtype in ('autoformcombo', 'itemselector'):
        field['values'] = item['values']
    if xtype=='checkbox':
        field['checked'] = value
    return field


class FormBuilder(object):
    implements(IFormBuilder)
    adapts(IInfo)

    def __init__(self, context):
        self.context = context

    def vocabulary(self, field):
        vocabulary = field.vocabulary
        if vocabulary is None:
            reg = getVocabularyRegistry()
            try:
                vocabulary = reg.get(self.context, field.vocabularyName)
            except VocabularyRegistryError:
                raise ValueError("Can't get values from vocabulary %s" %
                                 field.vocabularyName)
        return [(t.value, t.token) for t in vocabulary._terms]

    def fields(self):
        d = {}
        for iface in providedBy(self.context):
            f = zope.schema.getFields(iface)
            for k,v in f.iteritems():
                c = _dict(v)
                c['name'] = k
                c['value'] = getattr(self.context, k, None)
                if c['xtype'] in ('autoformcombo', 'itemselector'):
                    c['values'] = self.vocabulary(v)
                d[k] = c
        return d

    def groups(self):
        g = {}
        for k, v in self.fields().iteritems():
            g.setdefault(v['group'], []).append(v)
        for l in g.values():
            l.sort(key=ordergetter)
        return g

    def render(self, fieldsets=True):
        if not fieldsets:
            
            fields = sorted(self.fields().values(), key=ordergetter)
            form = map(_item, fields)
            return form
                            
        # group the fields 
        groups = self.groups()
        form = {
            'items': [_fieldset(k, v) for k,v in groups.iteritems()]
        }
        return form
        

