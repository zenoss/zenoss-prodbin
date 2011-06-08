###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

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
