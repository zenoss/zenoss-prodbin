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
__doc__="""Creates root node from where triggers will be managed."""

import Migrate
from Products.ZenModel.Trigger import TriggerManager, manage_addTriggerManager
from Products.Zuul.utils import safe_hasattr as hasattr

class Triggers(Migrate.Step):
    version = Migrate.Version(3,1,70)

    def cutover(self, dmd):
        if not hasattr(dmd, TriggerManager.root):
            manage_addTriggerManager(dmd)

Triggers()