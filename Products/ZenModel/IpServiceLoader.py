#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__ ='''IpServiceLoader

A script to load the IANA well known port numbers.

$Id: IpServiceLoader.py,v 1.5 2004/04/15 23:47:50 edahl Exp $'''

__version__ = "$Revision: 1.5 $"[11:-2]

import Globals #initalize imports correctly magic!

from Products.ZenUtils.BasicLoader import BasicLoader

from Products.ZenModel.ServiceClass import manage_addServiceClass
from Products.ZenModel.IpServiceClass import manage_addIpServiceClass
from Products.ZenModel.IpServiceClass import getIpServiceClassId

class IpServiceLoader(BasicLoader):

    def __init__(self, noopts=0, app=None):
        self.filename = os.path.join(os.path.dirname(__file__), 
                            "port-numbers.txt")
        BasicLoader.__init__(self, noopts, app, ignoreComments=False)
        ipserv = self.dmd.Services.IpServices
        privid = 'Privileged'
        self.privserv = ipserv._getOb(privid,None) 
        if not self.privserv:
            manage_addServiceClass(ipserv, privid)
            self.privserv = ipserv._getOb(privid)
        self.lastservice = None


    def loaderBody(self, line):
        linearray = line.split()
        if linearray[0] == "#" and self.lastservice:
            if line.find("@") > -1: return
            linearray[0] = ""
            desc = " ".join(linearray)
            self.lastservice.description += desc
            return
        elif len(linearray) < 2: return
        portindex = 0
        keyword = ''
        if linearray[0].find('/') == -1:
            keyword = linearray[0]
            portindex += 1
        port,proto = linearray[portindex].split('/')
        portindex += 1
        try:
            port = int(port)
        except:
            self.log.warn(
                "Bad port number found %s linenumber %d" % 
                (port, self.lineNumber))
            return
        descr = ' '.join(linearray[portindex:])
        if descr.find("Unassigned") > -1: return
        elif port <= 1024:
            id = getIpServiceClassId(proto, port)
            if not hasattr(self.privserv, id):
                manage_addIpServiceClass(self.privserv,proto,port,
                                        keyword=keyword, description=descr) 
                self.lastservice = self.privserv._getOb(id)
                self.log.info("Added IpServiceClass %s" % id)
        else:
            return True


if __name__ == "__main__":
    loader = IpServiceLoader()
    loader.loadDatabase()
    print "Database Load is finished!"
