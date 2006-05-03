#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""zenbuild

Build the zentinel portal object and the dmd database

$Id: DmdBuilder.py,v 1.11 2004/04/06 22:33:07 edahl Exp $"""

__version__ = "$Revision: 1.11 $"[11:-2]

import sys
import os

import Globals
import transaction

if not os.environ.has_key('ZENHOME'):
    print "ERROR: ZENHOME envrionment variable not set"
    sys.exit(1)

zenhome = os.environ['ZENHOME']

import Globals

from Products.ZenUtils.CmdBase import CmdBase

class zenbuild(CmdBase):
    
    sitename = "zport"
    
    def __init__(self):
        CmdBase.__init__(self)
        if not os.environ.has_key("ZENHOME"):
            print "ERROR: ZENHOME not set."
            sys.exit(1)
        zopeconf = os.path.join(os.environ['ZENHOME'], "etc/zope.conf")
        import Zope2
        Zope2.configure(zopeconf)
        self.app = Zope2.app()


    def buildOptions(self):
        CmdBase.buildOptions(self)
        self.parser.add_option('-u','--evtuser', dest="evtuser", default="root",
                help="username used to connect to the events database")
        self.parser.add_option('-p','--evtpass', dest="evtpass", default="",
                help="password used to connect to the events database")


    def build(self):
        site = getattr(self.app, self.sitename, None)
        if not site:
            from Products.ZenModel.ZentinelPortal import \
                manage_addZentinelPortal
            manage_addZentinelPortal(self.app, self.sitename)
            site = self.app._getOb(self.sitename)
            trans = transaction.get()
            trans.note("Initial ZentinelPortal load by zenbuild.py")
            trans.commit()
            print "ZentinelPortal loaded at %s" % self.sitename

        # build dmd
        from Products.ZenModel.DmdBuilder import DmdBuilder
        dmdBuilder = DmdBuilder(site,self.options.evtuser,self.options.evtpass)
        dmdBuilder.build()

        # Load RRD Data
        #from Products.ZenRRD.RRDLoader import RRDLoader
        #rrdloader = RRDLoader(noopts=True, app=self.app) 
        #rrdloader.loadDatabase()
        
        # Load IpService data
        #from Products.ZenModel.IpServiceLoader import IpServiceLoader
        #ipsvcloader = IpServiceLoader(noopts=True, app=self.app) 
        #ipsvcloader.loadDatabase()

        # Load reports
        from Products.ZenModel.ReportLoader import ReportLoader
        rl = ReportLoader(noopts=True, app=self.app) 
        rl.loadDatabase()

        
        # Load XML Data
        from Products.ZenModel.XmlDataLoader import XmlDataLoader
        dl = XmlDataLoader(noopts=True, app=self.app) 
        dl.loadDatabase()


if __name__ == "__main__":
    zb = zenbuild()
    zb.build()
