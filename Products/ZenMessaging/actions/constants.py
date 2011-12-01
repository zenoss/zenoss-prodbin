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

class AutoString(object):
    """
    For backwards compatibility during upgrades.
    ActionName.BlahBlah yields string 'BlahBlah'.
    ActionTargetType.FooBar yields string 'FooBar'.
    """
    def __getattr__(self, attr):
        return attr

ActionName = ActionTargetType = AutoString()
