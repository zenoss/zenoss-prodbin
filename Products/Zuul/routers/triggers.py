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

from Products import Zuul
from Products.ZenUtils.Ext import DirectRouter
from Products.ZenUtils.extdirect.router import DirectResponse

import logging

log = logging.getLogger('zen.triggers');

class TriggersRouter(DirectRouter):
    """
    Router for Triggers UI section under Events.
    """
    
    def _getFacade(self):
        return Zuul.getFacade('triggers', self)
    
    def getTriggers(self):
        return DirectResponse.succeed(data=self._getFacade().getTriggers())
    
    def addTrigger(self, name):
        return DirectResponse.succeed(data=self._getFacade().addTrigger(name))
        
    def removeTrigger(self, uuid):
        return DirectResponse.succeed(data=self._getFacade().removeTrigger(uuid))
        
    def getTrigger(self, uuid):
        return DirectResponse.succeed(data=self._getFacade().getTrigger(uuid))
        
    def updateTrigger(self, **data):
        response = self._getFacade().updateTrigger(**data)
        return DirectResponse.succeed(data=response)
    
    def parseFilter(self, source):
        try:
            response = self._getFacade().parseFilter(source)
            return DirectResponse.succeed(data=response)
        except Exception, e:
            log.exception(e)
            return DirectResponse.fail(
                'Error parsing filter source. Please check your syntax.')

