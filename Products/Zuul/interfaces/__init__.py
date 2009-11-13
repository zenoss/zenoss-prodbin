###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from zope.interface import Interface

class IFacade(Interface):
    """
    An API facade
    """

class IDataRootFactory(Interface):
    """
    Returns a DataRoot object from the current connection.
    """
    
class ISerializableFactory(Interface):
    """
    Calling implementations of this interface returns a python data structure
    suitable for serialization. The objects that these factories create can be
    passed to json.dumps().
    """

from events import *
from process import *
