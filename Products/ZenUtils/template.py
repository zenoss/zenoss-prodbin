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

class Template(object):
    def __init__(self, template_body):
        self.template_body = template_body
    
    def fill(self, **kwargs):
        _str = self.template_body % kwargs
        return _str.format(**kwargs)