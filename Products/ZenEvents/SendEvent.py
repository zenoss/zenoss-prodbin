###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import logging
import socket
import xmlrpclib

from Products.ZenUtils.Utils import  basicAuthUrl

class SendEvent(object):

    def __init__(self, agent, username, password, url):
        self.agent = agent
        self.url = basicAuthUrl(username, password, url)
        self.server = xmlrpclib.Server(self.url)
        severities = self.server.getSeverities()
        for name, value in severities:
            setattr(self, name, value)


    def sendEvent(self, deviceName, evclass, msg, severity, **kwargs):
        """
        Send a ZenEvent to the event manager.  Events must have:
        deviceName - which is the FQDN of the device
        evclass - the event class of the event
        msg - the event message
        severity - the severity of the event 

        agent - is the management collection system that the event came through

        Other potential fields are:

        """
        event = {}
        event['Node'] = deviceName
        event['Class'] = evclass
        event['Summary'] = msg
        event['Severity'] = severity
        event['Agent'] = self.agent
        event['Manager'] = socket.getfqdn()
        event.update(kwargs)
        try:
            self.server.sendEvent(event)
        except SystemExit: raise
        except:
            raise
            logging.exception("Event notification failed url %s", self.url)
