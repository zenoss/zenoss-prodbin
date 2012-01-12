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
from zope.component.interfaces import ObjectEvent

class DaemonLifecycleEvent(ObjectEvent):
    """
    Base class for zeneventd lifecycle events.
    """

class DaemonCreatedEvent(DaemonLifecycleEvent):
    """
    Fired at the end of zeneventd's constructor.
    """

class DaemonStartRunEvent(DaemonLifecycleEvent):
    """
    Fired when zeneventd is started and ready to listen.
    """

class SigTermEvent(DaemonLifecycleEvent):
    """
    Called when zeneventd receives a SIGTERM.
    """

class SigUsr1Event(DaemonLifecycleEvent):
    """
    Called when zeneventd receives a SIGUSR1 event -- that is,
    when "zeneventd debug" is run.
    """
    def __init__(self, daemon, signum):
        super(SigUsr1Event, self).__init__(daemon)
        self.signum = signum

class BuildOptionsEvent(DaemonLifecycleEvent):
    """
    Called when zeneventd is building its option parser.
    """
