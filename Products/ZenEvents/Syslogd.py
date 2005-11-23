"""A minimalistic syslogd.

2000-06-09/bb:  created
2000-06-12/bb:  added constants from syslog.h,
                config options for time format, stop string
"""
import sys, string, time, socket, re, os

import Globals

from Products.ZenEvents.SendEvent import SendEvent

# constants from syslog.h
LOG_EMERGENCY   = 0
LOG_ALERT       = 1
LOG_CRITICAL    = 2
LOG_ERRROR      = 3
LOG_WARNING     = 4
LOG_NOTICE      = 5
LOG_INFO        = 6
LOG_DEBUG       = 7

LOG_PRIMASK     = 0x07

def LOG_PRI(p): return p & LOG_PRIMASK
def LOG_MAKEPRI(fac, pri): return fac << 3 | pri

LOG_KERN        = 0 << 3
LOG_USER        = 1 << 3
LOG_MAIL        = 2 << 3
LOG_DAEMON      = 3 << 3
LOG_AUTH        = 4 << 3
LOG_SYSLOG      = 5 << 3
LOG_LPR         = 6 << 3
LOG_NEWS        = 7 << 3
LOG_UUCP        = 8 << 3
LOG_CRON        = 9 << 3
LOG_AUTHPRIV    = 10 << 3
LOG_FTP         = 11 << 3
LOG_LOCAL0      = 16 << 3
LOG_LOCAL1      = 17 << 3
LOG_LOCAL2      = 18 << 3
LOG_LOCAL3      = 19 << 3
LOG_LOCAL4      = 20 << 3
LOG_LOCAL5      = 21 << 3
LOG_LOCAL6      = 22 << 3
LOG_LOCAL7      = 23 << 3

LOG_NFACILITIES = 24
LOG_FACMASK     = 0x03F8
def LOG_FAC(p): return (p & LOG_FACMASK) >> 3

def LOG_MASK(pri): return 1 << pri
def LOG_UPTO(pri): return (1 << pri + 1) - 1
# end syslog.h

def LOG_UNPACK(p): return (p & LOG_FACMASK, LOG_PRI(p))

fac_values = {}     # mapping of facility constants to their values
fac_names = {}      # mapping of values to names
pri_values = {}
pri_names = {}
for i, j in globals().items():
    if i[:4] == 'LOG_' and type(j) == type(0):
        if j > LOG_PRIMASK or i == 'LOG_KERN':
            n, v = fac_names, fac_values
        else:
            n, v = pri_names, pri_values
        i = i[4:].lower()
        v[i] = j
        n[j] = i
del i, j, n, v


conf_pat = re.compile(r'''
    ^\s*            # leading space
    ([\w*]+)        # facility
    \.([=!]?)       # separator plus optional modifier
    ([\w*]+)        # priority
    \s+
    ([|@]?)         # target type fifo/remote host
    (\S+)           # target
    ''', re.VERBOSE)


SYSLOG_PORT = socket.getservbyname('syslog', 'udp')

from Products.ZenUtils.ZenDaemon import  ZenDaemon
from SocketServer import ThreadingUDPServer
from threadding import Lock

class Syslogd(ThreadingUDPServer, ZenDaemon):

    def __init__(self, addr='', port=SYSLOG_PORT, pri=LOG_DEBUG, 
            timefmt=None, magic=None):

        ThreaddingUDPServer.__init__(self, (addr, port), None)
        ZenDaemon.__init__(self)
        self.hostmap = {}       # client address/name mapping
        self.priority = pri
        self.timefmt = timefmt or '%b %d %H:%M:%S'
        self.stop_magic = magic or '_stop'
        self.hostmapLock = Lock() 
        self.log.info("syslog start")
        self.ev = SendEvent("syslog", self.options.zopeusername, 
                            self.options.zopepassword, self.options.zopeurl)
        self.ev.sendEvent(socket.getfqdn(), "SyslogStatus",
                        "syslog collector started", self.ev.Info,
                        Component="syslog")


    def resolvaddr(self, clientip):
        # build the client address/name mapping
        host = self.hostmap.get(clientip, False)
        if host: return host
        try:
            host = socket.gethostbyaddr(clientip)[0]
            #host = host.split('.')[0]       # keep only the host name
        except socket.error:
            host = clientip
        self.hostmap[clientip] = host   #GIL protected shared write
        return host


    def priParse(self, msg):
        """Extract log facility and priority, if present.
        """
        pri = None
        fac = None
        if msg[:1] == '<':
            pos = msg.find('>')
            fac, pri = LOG_UNPACK(int(msg[1:pos]))
            msg = msg[pos+1:]
        elif msg and msg[0] < ' ':
            fac, pri = LOG_KERN, ord(msg[0])
            msg = msg[1:]
        return fac, pri, msg


    def finish_request(self, (msg, sock), client_address):

        self.log.debug(msg)
        ipaddr = client_address[0]
        hostname = self.resolvaddr(ipaddr)
        evt = SyslogEvent(hostname, ipaddr, msg)
        self.ev.sendEvent(evt)



        evt.pri, evt.fac, msg = self.priparse(msg) 
        self.log.debug("fac=%s pri=%s", fac, pri)
        if pri < self.basePriority: 
            self.log.debug("droping event due to priority below threshold")
            return
        evt.facility = fac_names.get(fac,None)
        evt.priority = pri_names.get(pri,None)

        facility = "syslog"
        if msg.find(":") > -1:
            facility, msg = msg.split(":", 1)

        # map severity of message
        sev = 1
        if pri < 3: sev = 5
        elif pri == 3: sev = 4
        elif pri == 4: sev = 3
        elif 7 > pri < 4: sev = 2
        
        identifier = "|".join((host, "Syslog", facility, str(sev), msg))
        self.ev.sendEvent(host, "Syslog", msg, sev, Component=facility, 
                            Identifier=identifier,IpAddress=client)
        #self.log.info(client + ' ' + host + ': ' + msg.strip())

    
    
    def buildOptions(self):
        ZenDaemon.buildOptions(self)
        self.parser.add_option('-u', '--zopeusername',
                    dest='zopeusername', default="monitor",
                    help="Zope username to send events")
        self.parser.add_option('-p', '--zopepassword',
                    dest='zopepassword', default="monitor",
                    help="Zope password to send events")
        self.parser.add_option('--zopeurl',
                    dest='zopeurl', 
                    default="http://localhost:8080/zport/dmd/ZenEventManager",
                    help="Zope password to send events")


    def serve(self):
        "Run the service until it is stopped with the stop() method."
        self.running = 1
        while self.running:
            self.handle_request()


    def sigTerm(self, signum, frame):
        self.running = 0
        if os.path.exists(self.pidfile):
            self.log.info("delete pidfile %s", self.pidfile)
            os.remove(self.pidfile)
        self.log.info('Daemon %s shutting down' % self.__class__.__name__)
        try:
            self.ev.sendEvent(socket.getfqdn(), "SyslogStatus",
                        "syslog collector stopped", self.ev.Warning,
                        Component="syslog")
        except: pass # if this fails we still want to shutdown nicely



if __name__ == '__main__':
    Syslogd(timefmt='%H:%M:%S').serve()
