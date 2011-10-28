###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from zope.interface import Interface

class IAuditManager(Interface):
    """
    Announces messages so they can be tracked or handled.
    See __init__.py for usage.
    """
    def audit(self,
              category_,        # 'Source.ObjType.Action' or [source, objType, action, ...]
              object_=None,     # Target object matching the ObjType.
              skipFields_=(),   # Completely ignore fields with these names.
              maskFields_=(),   # Hide values of these field names, such as 'password'.
              oldData_=None,    # Old values in format {name:oldValue}
              data_=None,       # New values in format {name:value}
              **kwargs):        # New values in format name=value
        pass
