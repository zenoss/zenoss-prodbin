##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


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
