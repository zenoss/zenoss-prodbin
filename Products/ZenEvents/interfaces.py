##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import Interface

class ISendEvents(Interface):
    """
    Send events to the event system backend.
    """
   
    def sendEvents(self, events):
        """
        Send a list of events to the event system backend.
        """


    def sendEvent(self, event, keepopen=0):
        """
        Send a single event to the event system backend.
        """

class IEventPlugin(Interface):
    """
    Plugins that are looked up by zeneventd and executed.
    """
    def apply(event):
        """
        Apply the plugin to an event.
        """

class IPreEventPlugin(IEventPlugin):
    """
    Event plugins applied before transforms.
    """

class IPostEventPlugin(IEventPlugin):
    """
    Event plugins applied after transforms and before passing to ZEP.
    """

class IEventIdentifierPlugin(Interface):
    """
    Plugins used by an IdentifierPipe to do custom event identification
    """
    def resolveIdentifiers(event, eventProcessorMgr):
        """
        Update the identifiers in the event based on custom identifier resolution logic.
        """
