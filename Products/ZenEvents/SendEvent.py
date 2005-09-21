
import logging
import socket
import xmlrpclib

from Products.ZenUtils.Utils import basicAuthUrl

class SendEvent(object):

    def __init__(self, agent, username, password, url):
        self.agent = agent
        self.url = basicAuthUrl(username, password, url)
        self.server = xmlrpclib.Server(self.url)
        severities = self.server.getSeverities()
        for name, value in severities:
            setattr(self, name, value)


    def sendEvent(self, deviceName, component, severity, msg, **kwargs):
        """
        Send a ZenEvent to the event manager.  Events must have:
        deviceName - which is the FQDN of the device
        component - sub component of the event (i.e. process, interface, etc)
        severity - the severity of the event 
        msg - the event message

        agent - is the management collection system that the event came through

        Other potential feilds are:

        """
        event = {}
        event['Node'] = deviceName
        event['AlertGroup'] = component
        event['Severity'] = severity
        event['Summary'] = msg
        event['Agent'] = self.agent
        event['Manager'] = socket.getfqdn()
        event.update(kwargs)
        try:
            self.server.sendEvent(event)
        except SystemExit: raise
        except:
            raise
            logging.exception("Event notification failed url %s", self.url)
