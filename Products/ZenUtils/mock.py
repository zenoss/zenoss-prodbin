###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

class MockObject(object):
    """
    An object that takes a hashmap and uses it for the attributes on
    the object.  Setting attributes is ignored.  Retrieving an
    unknown attribute returns an empty MockObject.  The key 'return__' is
    special in that its corresponding value will be returned if the object
    is called as a function.

    >>> a=MockObject(b='c')
    >>> a.b
    'c'
    >>> a.d
    {}
    >>> a.d.e
    {}
    >>> x=MockObject(return__=5)
    >>> y=MockObject(z=x)
    >>> y.z()
    5
    """
    def __call__(self, *args, **kw):
        return self.attrs.get( 'return__', None )

    def __init__(self, **kw):
        self.attrs = kw.copy()

    def __getattr__(self, item):
        if item == 'attrs':
            return self.__dict__['attrs']

        try:
            return self.attrs[item]
        except KeyError:
            return MockObject()

    def __repr__(self):
        return str(self.attrs)

    def __str__(self):
        return self.__repr__()
