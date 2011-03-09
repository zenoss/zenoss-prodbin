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

class SpecialDict(object):
    def __init__(self, data):
        self_dict = object.__getattribute__(self, '__dict__')
        self_dict.update(data)

    def __getattr__(self, item):
        self_dict = object.__getattribute__(self, '__dict__')
        try:
            return self_dict[item]
        except KeyError:
            return None

class Template(object):
    def __init__(self, template_body):
        self.template_body = template_body
    
    def fill(self, **kwargs):
        def dict_to_obj(d):
            for k,v in d.iteritems():
                if isinstance(v, dict):
                    d[k] = dict_to_obj(v)
            return SpecialDict(d)
        
        return self.template_body.format(**dict_to_obj(kwargs).__dict__)