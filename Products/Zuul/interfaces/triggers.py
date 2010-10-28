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

from Products.Zuul.interfaces import IFacade

class ITriggersFacade(IFacade):
    def getTriggers():
        pass

    def addTrigger(name):
        pass

    def removeTrigger(uuid):
        pass

    def getTrigger(uuid):
        pass
        
    def updateTrigger(uuid, **data):
        pass
    
    def parseFilter(source):
        pass