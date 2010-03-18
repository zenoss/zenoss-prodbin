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

from zope.schema._field import Text as ZSText, TextLine, Bool, Int, Float
from zope.schema._field import Tuple, List, Password, Choice as ZSChoice

class FieldMixin(object):
    """
    A mixin providing extra attributes to zope.schema.
    """
    def __init__(self, xtype=None, order=None, group=None, vtype=None, 
                 *args, **kwargs):
        super(FieldMixin, self).__init__(*args, **kwargs)
        l = locals()
        for f in ('xtype', 'order', 'group', 'vtype'):
            value = l[f]
            if value is not None:
                setattr(self, f, value)

def _mixedIn(klass, **kwargs):
    """
    Return a class with FieldMixin mixed in and default attributes set.
    """
    return type(klass.__name__, (FieldMixin, klass), kwargs)

Text = _mixedIn(ZSText, xtype='textfield')
TextLine = _mixedIn(TextLine, xtype='textarea')
Bool = _mixedIn(Bool, xtype='checkbox')
Int = _mixedIn(Int, xtype='numberfield')
Float = _mixedIn(Float, xtype='numberfield')
Tuple = _mixedIn(Tuple, xtype='textarea')
List = _mixedIn(List, xtype='textarea')
Choice = _mixedIn(ZSChoice, xtype='autoformcombo')
MultiChoice = _mixedIn(ZSChoice, xtype='itemselector')
Password = _mixedIn(Password, xtype='textfield')
Entity = _mixedIn(ZSText, xtype='linkfield')
