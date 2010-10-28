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
from interfaces import IProtobufJsonizable

TRIGGER_FILTER_API_VERSION = 1
TRIGGER_FILTER_CONTENT_TYPE = 'python'

class EventTriggerProtobuf(object):
    """
    Fills up the properties of an EventTrigger protobuf. This does not use the 
    ObjectProtobuf class because EventTriggers are not stored in zope.
    """
    _base_keys = ['uuid','name','delay_seconds','repeat_seconds','enabled','send_clear']
    _filter_keys = ['api_version','content_type','content']

    implements(IProtobufJsonizable)

    def __init__(self, proto):
        self.proto = proto
    
    def fill(self, json_obj):
        self.json_obj = json_obj
        for key in self._base_keys:
            if key in self.json_obj:
                setattr(self.proto, key, self.json_obj[key])
        if 'filter' in self.json_obj:
            for key in self._filter_keys:
                if key in self.json_obj['filter']:
                    setattr(self.proto.filter, key, self.json_obj['filter'][key])
                else:
                    if key == 'api_version':
                        setattr(self.proto.filter, key, TRIGGER_FILTER_API_VERSION)
                    if key == 'content_type':
                        setattr(self.proto.filter, key, TRIGGER_FILTER_CONTENT_TYPE)
    
    def json_friendly(self):
        obj = {}
        for key in self._base_keys:
            obj[key] = getattr(self.proto, key)

        obj['filter'] = {}
        for key in self._filter_keys:
            obj['filter'][key] = getattr(self.proto.filter, key)
        return obj
        
class EventTriggerSetProtobuf(object):
    
    def __init__(self, proto):
        self.proto = proto
    
    def fill(self, json_obj):
        self.json_obj = json_obj
        if 'triggers' in self.json_obj:
            for t in self.json_obj['triggers']:
                trigger = self.proto.triggers.add()
                IProtobufJsonizable(trigger).fill(t)
    
    def json_friendly(self):
        obj = []
        if hasattr(self.proto, 'triggers'):
            for t in self.proto.triggers:
                trigger_obj = IProtobufJsonizable(t).json_friendly()
                obj.append(trigger_obj)
        return obj