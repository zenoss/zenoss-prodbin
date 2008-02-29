###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

class TestClass:

    def __init__(self, *args, **kw):
        self.args = args
        self.kw = kw

    def echo(self, *args, **kw):
        return args, kw
    
    def getInit(self):
        return self.args, self.kw

    def error(self, message):
        raise AttributeError, message

    def sleep(self, seconds):
        import time
        time.sleep(seconds)
        return seconds
