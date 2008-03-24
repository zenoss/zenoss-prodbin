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
__doc__ = """
A Null-Object implementation of ProcessProxy, for when we don't really
want a Proxy."""

class NullProxy:
    
    def __init__(self, filename, classname):
        self.filename = filename
        self.classname = classname
        self.obj = None

    def start(self, timer, *args, **kw):
        fp = open(self.filename)
        try:
            locals = {}
            exec fp in locals
            self.obj = locals[self.classname](*args, **kw)
        finally:
            fp.close()

    def stop(self):
        if self.obj and hasattr(self.obj, 'close'):
            self.obj.close()
        self.obj = None

    def boundedCall(self, timer, method, *args, **kw):
        return getattr(self.obj, method)(*args, **kw)
