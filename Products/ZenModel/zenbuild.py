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
import sys,os
import transaction

if not os.environ.has_key('ZENHOME'):
    print "ERROR: ZENHOME envrionment variable not set"
    sys.exit(1)

zenhome = os.environ['ZENHOME']

import Globals

from Products.ZenUtils.ZCmdBase import ZCmdBase

class zenbuild(ZCmdBase):
    
    def __init__(self):
        ZCmdBase.__init__(self)
        self.options.dataroot = "/"
        self.dmd = None


    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('-f', '--filename',
                dest="schema",
                default="schema.data",
                help="Location of the Dmd schema")
        self.parser.add_option('-s', '--sitename',
                dest="sitename",
                default="zport",
                help="name of portal object")


    def build(self):
        site = getattr(self.app, options.sitename, None)
        if site: return
        from Products.ZenModel.ZentinelPortal import manage_addZentinelPortal
        manage_addZentinelPortal(app, options.sitename, schema=options.schema)
        site = self.app._getOb(options.sitename)
        trans = transaction.get()
        trans.note("Initial ZentinelPortal load by zenbuild.py")
        trans.commit()
        print "ZentinelPortal loaded at %s" % options.sitename

        # Load RRD Data
        rrdloader = RRDLoader(noopts=True, app=self.app) 
        rrdloader.loadDatabase()

        # Load IpService data
        ipsvcloader = IpServiceLoader(noopts=True, app=self.app) 
        ipsvcloader.loadDatabase()
