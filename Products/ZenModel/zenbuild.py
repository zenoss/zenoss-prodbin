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

from Products.ZenUtils import Security
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
        self.parser.add_option('-s','--evthost', dest="evthost", default="root",
                help="events database hostname")
        self.parser.add_option('-u','--evtuser', dest="evtuser", default="root",
                help="username used to connect to the events database")
        self.parser.add_option('-p','--evtpass', dest="evtpass", default="",
                help="password used to connect to the events database")
        self.parser.add_option('-d','--evtdb', dest="evtdb", default="events",
                help="name of events database")
        self.parser.add_option('--smtphost', dest="smtphost", default="localhost",
                help="smtp host")
        self.parser.add_option('--smtpport', dest="smtpport", default=25,
                help="smtp port")
        self.parser.add_option('--snpphost', dest="snpphost", default="localhost",
                help="snpp host")
        self.parser.add_option('--snppport', dest="snppport", default=444,
                help="snpp port")


    def build(self):
        site = getattr(self.app, self.sitename, None)
        if site is not None:
            print "zport portal object exits; exiting."
            return
        
        from Products.ZenModel.ZentinelPortal import manage_addZentinelPortal
        manage_addZentinelPortal(self.app, self.sitename)
        site = self.app._getOb(self.sitename)

        # build index_html
        if self.app.hasObject('index_html'):
            self.app._delObject('index_html')
        from Products.PythonScripts.PythonScript import manage_addPythonScript
        manage_addPythonScript(self.app, 'index_html')
        newIndexHtml = self.app._getOb('index_html')
        text = 'container.REQUEST.RESPONSE.redirect("/zport/dmd/")\n'
        newIndexHtml.ZPythonScript_edit('', text)
        
        # build standard_error_message
        if self.app.hasObject('standard_error_message'):
            self.app._delObject('standard_error_message')
        file = open('%s/Products/ZenModel/dtml/standard_error_message.dtml' %
                        zenhome)
        try:
            text = file.read()
        finally:
            file.close()
        import OFS.DTMLMethod
        OFS.DTMLMethod.addDTMLMethod(self.app, id='standard_error_message',
                                        file=text)

        # Convert the acl_users folder at the root to a PAS folder and update
        # the login form to use the Zenoss login form
        Security.replaceACLWithPAS(self.app, deleteBackup=True)

        trans = transaction.get()
        trans.note("Initial ZentinelPortal load by zenbuild.py")
        trans.commit()
        print "ZentinelPortal loaded at %s" % self.sitename

        # build dmd
        from Products.ZenModel.DmdBuilder import DmdBuilder
        dmdBuilder = DmdBuilder(site, 
                                self.options.evthost, 
                                self.options.evtuser, 
                                self.options.evtpass,
                                self.options.evtdb, 
                                self.options.smtphost, 
                                self.options.smtpport, 
                                self.options.snpphost, 
                                self.options.snppport)
        dmdBuilder.build()
        transaction.commit() 
        # Set smtp and snpp values
        

        # Load reports
        from Products.ZenReports.ReportLoader import ReportLoader
        rl = ReportLoader(noopts=True, app=self.app)
        rl.loadDatabase()

        # Load XML Data
        from Products.ZenModel.XmlDataLoader import XmlDataLoader
        dl = XmlDataLoader(noopts=True, app=self.app)
        dl.loadDatabase()


if __name__ == "__main__":
    zb = zenbuild()
    zb.build()
