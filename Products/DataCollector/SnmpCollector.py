#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

import logging
from DateTime import DateTime

from twisted.internet import reactor

import Globals
import transaction

from Products.SnmpCollector.SnmpSession import SnmpSession, ZenSnmpError
from pysnmp.error import PySnmpError

from SnmpClient import SnmpClient
from DataCollector import DataCollector
from Exceptions import *
    
zenmarker = "__ZENMARKER__"

slog = logging.getLogger("SnmpCollector")

def findSnmpCommunity(context, name, community=None, port=None):
    """look for snmp community based on list we get through aq"""
    if community: communities = (community,)
    else: communities = getattr(context, "zSnmpCommunities", ())
    if not port: port = getattr(context, "zSnmpPort", 161)
    session = SnmpSession(name, timeout=3, port=port)
    oid = '.1.3.6.1.2.1.1.5.0'
    retval = None
    for community in communities: #aq
        session.community = community
        try:
            session.get(oid)
            retval = session.community
            break
        except (SystemExit, KeyboardInterrupt): raise
        except: pass #keep trying until we run out
    return retval 


class SnmpCollector(DataCollector):
    

    def collectDevice(self, device, community=None, port=0, snmpver="v1"):
        device = self.resolveDevice(device)
        if not community: community = device.zSnmpCommunity
        if not port: port = device.zSnmpPort
        client = None
        plugins = []
        try:
            if (self.checkCollection(device) or 
                self.checkCiscoChange(device, community, port)):
                slog.info('Collecting device %s' % device.id)
                plugins = self.selectPlugins(device,"snmp")
                client = SnmpClient(device.id, port, community, 
                            snmpver, self.options, device, self, 
                            self.log, plugins)
        except (SystemExit, KeyboardInterrupt): raise
        except:
            slog.exception('Error collecting data from %s', device.id)
        if not client or not plugins: 
            slog.warn("client failed to initialize or no plugins found")
            return
#        if self.options.debug:
        self.clients[client] = 1
        client.run()
        if self.single:
            self.log.debug("reactor start single-device")
            reactor.run(False)
#        else:
#            self.collthread.runClient(client)



    def checkCollection(self, device):
        age = device.getSnmpLastCollection()+self.collage
        if device.getSnmpStatusNumber() > 0 and age >= DateTime():
            slog.info("skipped collection of %s" % device.getId())
            return False
        return True


    def checkCiscoChange(self, device, community, port):
        """Check to see if a cisco box has changed.
        """
        if self.options.force: return True
        snmpsess = SnmpSession(device.id, community=community, port=port)
        if not device.snmpOid.startswith(".1.3.6.1.4.1.9"): return True
        lastpolluptime = device.getLastPollSnmpUpTime()
        slog.debug("lastpolluptime = %s", lastpolluptime)
        try:
            lastchange = snmpsess.get('.1.3.6.1.4.1.9.9.43.1.1.1.0').values()[0]
            slog.debug("lastchange = %s", lastchange)
            if lastchange == lastpolluptime: 
                slog.info(
                    "skipping cisco device %s no change detected", device.id)
                return False
            else:
                device.setLastPollSnmpUpTime(lastchange)
        except (ZenSnmpError, PySnmpError): pass
        return True


    def findSnmpCommunity(self, name, device, port=161):
        """look for snmp community based on list we get through aq"""
        return findSnmpCommunity(device, name, port=port)
                    

if __name__ == '__main__':
    snmpcoll = SnmpCollector()
    snmpcoll.main()
