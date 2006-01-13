#################################################################
#
#   Copyright (c) 2005 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

import sys
import re
import socket

import Globals

import transaction

from Products.ZenUtils.Exceptions import ZentinelException
from Products.ZenEvents.ZenEventClasses import PingStatus
from Products.ZenEvents.Event import Event
from Products.PingMonitor.Ping import Ping

from zenmodeler import ZenModeler
from SnmpSession import SnmpSession, ZenSnmpError

class NoSnmp(ZentinelException):
    """Can't open an snmp connection to the device."""


class ZenDisc(ZenModeler):


    def __init__(self, noopts=0,app=None,single=True):
        ZenModeler.__init__(self, noopts, app, single)


    def discoverRouters(self, rootdev, seenips=[]):
        """Discover all default routers based on dmd configuration.
        """
        for ip in rootdev.followNextHopIps():
            if ip in seenips: continue
            self.log.info("device '%s' next hop '%s'", rootdev.id, ip)
            seenips.append(ip)
            router = self.discoverDevice(ip,devicepath="/Network/Router")
            if not router: continue
            self.discoverRouters(router, seenips)
            

    def discoverIps(self):
        """Ping all ips create if nessesary and perform reverse lookup.
        """
        ips = []
        ping = Ping(tries=self.options.tries, timeout=self.options.timeout,
                    chunkSize=self.options.chunkSize)
        nets = self.dmd.Networks
        pingthresh = getattr(self.dmd.Networks, "zPingFailThresh", 168)
        for net in nets.getSubNetworks():
            if not getattr(net, "zAutoDiscover", False): continue
            self.log.info("discover network '%s'", net.id)
            goodips, badips = ping.ping(net.fullIpList())
            for ip in goodips:
                ipobj = net.createIp(ip) 
                if not ipobj.device():
                    ips.append(ip)
            for ip in badips:
                ipobj = self.dmd.Networks.findIp(ip)
                if ipobj:
                    if ipobj.getStatus(PingStatus) > pingthresh:
                        net.ipaddresses.removeRelation(ipobj)
                    else:
                        self.sendEvent(ipobj)
            transaction.commit()
        self.log.info("discovered %s active ips", len(ips))    
        return ips
       

    def sendEvent(self, ipobj):
        """Send an ip down event.  These are used to cleanup unused ips.
        """
        ip = ipobj.id
        dev = ipobj.device()
        if dev: 
            devname = dev.id
            comp = ipobj.interface().id
            sev = 4
        else: 
            devname = comp = ip
            sev = 2
        evt = Event(device=devname,ipAddress=ip,eventKey=ip,
                    component=comp,eventClass=PingStatus,
                    summary="ip %s is down"%ip, severity=sev,
                    agent="Discover")
        self.dmd.ZenEventManager.sendEvent(evt)

    
    def discoverDevices(self, ips, devicepath="/Discovered"):
        """Discover devices by active ips that are not associated with a device.
        """
        for ip in ips: self.discoverDevice(ip)


    iptype = re.compile("^\d+\.\d+\.\d+\.\d+$").search

    def discoverDevice(self, ip, devicepath="/Discovered", sync=False):
        devname = ""
        if not self.iptype(ip):
            devname = ip
            ip = socket.gethostbyname(ip)
        try:
            ipobj = self.dmd.Networks.findIp(ip)
            if ipobj:
                if not getattr(ipobj, "zAutoDiscover", True): 
                    self.log.info("ip '%s' on no auto-discover, skipping",ip)
                    return
                dev = ipobj.device() 
                if dev:
                    if not self.options.remodel:
                        self.log.info("ip '%s' on device '%s' skiping",
                                        ip, dev.id)
                        return dev.primaryAq()
                    else:
                        self.log.info("ip '%s' on device '%s' remodel",
                                        ip, dev.id)
            community, port, ver, snmpname = self.findCommunity(ip,devicepath)
            self.log.debug("device community = %s", community)
            self.log.debug("device name = %s", snmpname)
            if not devname:
                try:
                    if snmpname and socket.gethostbyname(snmpname):
                        devname = snmpname
                except: pass
                try:
                    if (not devname and ipobj.ptrName 
                        and socket.gethostbyname(ipobj.ptrName)):
                        devname = ipobj.ptrName
                except: pass
                if not devname:
                    self.log.warn("unable to name device using ip '%s'", ip)
                    devname = ip
            self.log.info("device name '%s' for ip '%s'", devname, ip)
            dev = self.devroot(devicepath).createInstance(devname)
            dev.manage_editDevice(zSnmpCommunity=community, 
                                  zSnmpPort=port, zSnmpVer=ver,
                                  statusMonitors=["localhost"], 
                                  cricketMonitor="localhost")
            transaction.commit()
            self.collectDevice(dev)
            return dev
        except NoSnmp, e:
            self.log.warn(e)
            #FIXME add event showing problem so we don't remodel later
        except Exception, e:
            self.log.exception("faied device discovery for '%s'", ip)


    def devroot(self, devicepath):
        """Return and create if nesessary devicepath.
        """
        return self.dmd.Devices.createOrganizer(devicepath)

    
    def findCommunity(self, ip, devicepath):
        """Find the snmp community for an ip address using zSnmpCommunities.
        """
        devroot = self.devroot(devicepath)
        communities = getattr(devroot, "zSnmpCommunities", ())
        port = getattr(devroot, "zSnmpPort", 161)
        session = SnmpSession(ip, timeout=2, port=port)
        sysTableOid = '.1.3.6.1.2.1.1'
        oid = '.1.3.6.1.2.1.1.5.0'
        goodcommunity = ""
        devname = ""
        snmpver = "v1"
        for community in communities:
            session.community = community
            try:
                devname = session.get(oid).values()[0]
                goodcommunity = session.community
# FIXME - v2 queries don't take multiple head oids which needs to be
#           reconciled with v1 where we want that as an optimization.
#           will revisit when I have more time. -EAD
#                try:
#                    session.getTable(sysTableOid, bulk=True)
#                    snmpver="v2"
#                except (SystemExit, KeyboardInterrupt): raise
#                except: snmpver="v1" 
                break
            except (SystemExit, KeyboardInterrupt): raise
            except: pass #keep trying until we run out
        else:
            raise NoSnmp("no snmp found for ip = %s" % ip)
        return (goodcommunity, port, snmpver, devname) 


    def run(self):
        myname = socket.getfqdn()
        self.log.info("my hostname = %s", myname)
        try:
            myip = socket.gethostbyname(myname)
            self.log.info("my ip = %s", myip)
        except socket.error, e:
            self.log.warn("failed lookup of my ip for name %s", myname) 
        me = self.dmd.Devices.findDevice(myname)
        if not me or self.options.remodel:
            me = self.discoverDevice(myname, devicepath="/") 
        if not me:
            raise SystemExit("snmp discover of self '%s' failed" % myname)
        if not myip: myip = me.getManageIp()
        if not myip: 
            raise SystemExit("can't find my ip for name %s" % myname)
        self.discoverRouters(me, [myip])
        if self.options.routersonly:
            self.log.info("only routers discovered, skiping ping sweep.")
        else:
            ips = self.discoverIps()
            self.discoverDevices(ips)
        self.stop()


    def buildOptions(self):
        ZenModeler.buildOptions(self)
        self.parser.add_option('--remodel', dest='remodel',
                    action="store_true",
                    help="remodel existing objects")
        self.parser.add_option('--routers', dest='routersonly',
                    action="store_true",
                    help="only discover routers")
        self.parser.add_option('--tries', dest='tries', default=1, type="int",
                    help="how many ping tries")
        self.parser.add_option('--timeout', dest='timeout', 
                    default=2, type="float",
                    help="ping timeout in seconds")
        self.parser.add_option('--chunk', dest='chunkSize', 
                    default=10, type="int",
                    help="number of in flight ping packets")


if __name__ == "__main__":
    try:
        d = ZenDisc()
        d.run()
    except (SystemExit, KeyboardInterrupt):
        raise
    except Exception, e:
        print "Error: " + str(e)
