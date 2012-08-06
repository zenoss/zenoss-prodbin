##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zenoss.protocols.protobufs.zep_pb2 import STATUS_NEW, STATUS_ACKNOWLEDGED, \
    SEVERITY_CRITICAL, SEVERITY_ERROR, SEVERITY_WARNING
from Products.Zuul import getFacade
from Products.ZenReports.AliasPlugin import AliasPlugin
from Products.ZenEvents.ZenEventClasses import Status_Ping
from Products.ZenEvents.events2.proxy import EventProxy



class statuses(AliasPlugin):
    """
    Gets a list of devices based on if they have snmp status issues
    """

    def _getEvents(self, dmd, eventClass):
        """
        Returns all the open critical, warning or error events for the event class.
        """
        zep = getFacade('zep', dmd)
        event_filter = zep.createEventFilter(severity=[SEVERITY_WARNING,SEVERITY_ERROR,SEVERITY_CRITICAL],
                                             status=[STATUS_NEW,STATUS_ACKNOWLEDGED],                                                                                             event_class=filter(None, [eventClass])                                             
                                             )
                                             
        return zep.getEventSummaries(0, filter=event_filter)        

    def _getDevices(self, dmd, results, eventClass):
        """
        Look up the devices from the events. 
        """        
        events = results['events']
        for event in events:
            occurrence = event['occurrence'][0]
            actor = occurrence['actor']['element_identifier']            
            dev = dmd.Devices.findDevice(actor)
            if not dev:
                continue
            
            # if it is a STATUS_PING make sure it is against the manageIp IpInterface
            if eventClass == Status_Ping:                
                compId = occurrence['actor'].get('element_sub_identifier')                
                try:                    
                    iface = dev.os.interfaces._getOb(compId)
                    if dev.getManageIp() in [ip.partition("/")[0] for ip in iface.getIpAddresses()]:
                        yield dev                    
                except AttributeError:
                    # the component on this event isn't an IpInterface
                    continue            
            else:
                # an event class other than STATUS_PING can go against the device
                yield dev
    
    def run(self, dmd, args):
        eventClass = args['eventclass']
        results = self._getEvents(dmd, eventClass)        
        return self._getDevices(dmd, results, eventClass)
                                 
