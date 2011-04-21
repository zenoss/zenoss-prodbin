###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import logging
log = logging.getLogger('zen.actioninfos')

from zope.interface import implements

from Products.ZenModel.NotificationSubscription import NotificationSubscription

from Products.Zuul.infos import InfoBase
from Products.Zuul.interfaces.actions import IEmailActionContentInfo, IPageActionContentInfo, ICommandActionContentInfo, ISnmpTrapActionContentInfo
from zope.schema.fieldproperty import FieldProperty

_marker = object()

class ActionFieldProperty(FieldProperty):
    """
    We store action content properties in a container on the NotificationSubscription.
    This class will act mostly like a FieldProperty - it is extended because we
    have to proxy the property request into the content property on the object
    that's been adapted into an IInfo object. The __init__ signature is different
    than that of a FieldProperty for convenience.
    """
    def __init__(self, interfaceKlass, name):
        self.__field = interfaceKlass[name]
        self.__name = name

    def __get__(self, inst, klass):
        if inst is None:
            return self

        value = inst.__dict__.get('_object').content.get(self.__name, _marker)
        if value is _marker:
            field = self.__field.bind(inst)
            value = getattr(field, 'default', _marker)
            if value is _marker:
                raise AttributeError(self.__name)
        return value

    def __set__(self, inst, value):
        field = self.__field.bind(inst)
        field.validate(value)
        if field.readonly and inst.__dict__.get('_object').content.has_key(self.__name):
            raise ValueError(self.__name, 'field is readonly')
        inst.__dict__.get('_object').content[self.__name] = value

    def __getattr__(self, name):
        if hasattr(self, name):
            return getattr(self, name)
        else:
            return getattr(self.__field, name)


class EmailActionContentInfo(InfoBase):
    implements(IEmailActionContentInfo)

    body_content_type = ActionFieldProperty(IEmailActionContentInfo, 'body_content_type')
    subject_format = ActionFieldProperty(IEmailActionContentInfo,'subject_format')
    body_format = ActionFieldProperty(IEmailActionContentInfo, 'body_format')
    clear_subject_format = ActionFieldProperty(IEmailActionContentInfo, 'clear_subject_format')
    clear_body_format = ActionFieldProperty(IEmailActionContentInfo, 'clear_body_format')

class PageActionContentInfo(InfoBase):
    implements(IPageActionContentInfo)

    clear_subject_format = ActionFieldProperty(IEmailActionContentInfo, 'clear_subject_format')
    subject_format = ActionFieldProperty(IPageActionContentInfo, 'subject_format')


class CommandActionContentInfo(InfoBase):
    implements(ICommandActionContentInfo)

    action_timeout = ActionFieldProperty(ICommandActionContentInfo, 'action_timeout')
    body_format = ActionFieldProperty(ICommandActionContentInfo, 'body_format')
    clear_body_format = ActionFieldProperty(ICommandActionContentInfo, 'clear_body_format')


class SnmpTrapActionContentInfo(InfoBase):
    implements(ISnmpTrapActionContentInfo)

    action_destination = ActionFieldProperty(ISnmpTrapActionContentInfo, 'action_destination')












