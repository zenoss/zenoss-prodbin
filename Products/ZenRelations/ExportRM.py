#################################################################
#
#   Copyright (c) 2003 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""ExportRM

Export RelationshipManager objects from a zope database

$Id: ExportRM.py,v 1.1 2003/04/23 21:25:58 edahl Exp $"""

__version__ = "$Revision: 1.1 $"[11:-2]

import sys

import Globals

from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenRelations.RelationshipManager import RelationshipManager

class ExportRM(ZCmdBase):

    def __init__(self):
        ZCmdBase.__init__(self)
        if not self.options.outfile:
            self.outfile = sys.stdout
        else:
            self.outfile = open(self.options.outfile, 'w')
        
    
    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZCmdBase.buildOptions(self)
        self.parser.add_option('-o', '--outfile',
                    dest="outfile",
                    help="output file for export default is stdout")


    def export(self, root=None):
        if not root: 
            root = self.dataroot
        if hasattr(root, "exportXml"):
            self.outfile.write("""<?xml version="1.0"?>\n""")
            self.outfile.write("<objects>\n")
            root.exportXml(self.outfile,True)
            self.outfile.write("</objects>\n")
        else:
            print "ERROR: root object not a exportable (exportXml not found)"
            


if __name__ == '__main__':
    ex = ExportRM()
    ex.export()
