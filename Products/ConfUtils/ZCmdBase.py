#################################################################
#
#   Copyright (c) 2003 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""CmdBase

Add data base access functions for command line programs

$Id: ZCmdBase.py,v 1.9 2004/02/16 17:19:31 edahl Exp $"""

__version__ = "$Revision: 1.9 $"[11:-2]

from CmdBase import CmdBase
from Utils import getObjByPath

class DataRootError(Exception):pass

class ZCmdBase(CmdBase):


    def __init__(self, noopts=0, app=None):
        CmdBase.__init__(self, noopts)
        self.dataroot = None
        self.app = app
        self.getDataRoot(app)


    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        CmdBase.buildOptions(self)
        self.parser.add_option('-R', '--dataroot',
                    dest="dataroot",
                    default="/zport/dmd",
                    help="root object for data load (i.e. /zport/dmd)")


    def getDataRoot(self, app):
        if not self.dataroot:
            if not self.app: 
                import Zope
                self.app = Zope.app()
            self.dataroot = getObjByPath(self.app, self.options.dataroot)
            self.dmd = self.dataroot
            if not self.dataroot:
                raise DataRootError, "Data root %s not found " \
                                        % self.options.dataroot


    def getDmdObj(self, path):
        """return an object based on a path starting from the dmd"""
        return getObjByPath(self.dataroot, path)
