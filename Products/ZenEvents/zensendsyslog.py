import sys
import os
import socket
import Globals
zhome = os.environ['ZENHOME']
logdir = os.path.join(zhome, "log")
defaultInfile = os.path.join(logdir, "origsyslog.log")

from Products.ZenUtils.CmdBase import CmdBase

SYSLOG_PORT = socket.getservbyname('syslog', 'udp')

class ZenSendSyslog(CmdBase):


    def __init__(self):
        CmdBase.__init__(self)
        self.host = socket.gethostbyname(self.options.host)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  

    def run(self):
        self.log.info("sending messages to host %s", self.host)
        for line in open(self.options.infile).readlines():
            line = line.strip()
            if not line or line.startswith("#"): continue
            self.log.debug(line)
            self.sock.sendto(line, (self.host, SYSLOG_PORT))
            
    
    def buildOptions(self):
        CmdBase.buildOptions(self)
        self.parser.add_option('--infile',
            dest='infile', default=defaultInfile,
            help="file from which to draw events")
        
        self.parser.add_option('-H', '--host',
            dest='host', default='localhost',
            help="host to send to")


if __name__ == "__main__":
    sender = ZenSendSyslog()
    sender.run()
