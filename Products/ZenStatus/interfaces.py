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

from Products.ZenCollector import interfaces
from zope import interface

class IPingTask(interfaces.IScheduledTask):
    """
    Task to perform process pings on an ip.
    """

    def processPingResult(pingResult):
        """
            Process a ping result.
        """
        pass


class IPingTaskFactory(interfaces.IScheduledTaskFactory):
    """
    Factory to create PingTasks.
    """
    pass


class IPingCollectionPreferences(interfaces.ICollectorPreferences):
    """
    Class to customize app startup based on ping backend.
    """
    pass


class IPingResult(interface.Interface):
    """
    Class to store results from ping scan.
    """


    timestamp = interface.Attribute("""
        Timestamp of when ping was returned (seconds since epoch).
        """)

    address = interface.Attribute("""
        Address of the host
        """)
    
    trace = interface.Attribute("""
        traceroute of the host
        """)
    
    getStatusString = interface.Attribute("""
        status string: up or down
        """)
    
    isUp = interface.Attribute("""
        true if host is up, false if host is down
        """)

    rtt = interface.Attribute("""
        round trip time aka ping time aka rtt; nan if host was down
        """)

    variance = interface.Attribute("""
        variance of the rtt; nan if host was down
        """)

    stdDeviation = interface.Attribute("""
        standard deviation of the rtt; nan if host was down
        """)

