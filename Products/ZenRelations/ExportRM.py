#################################################################
#
#   Copyright (c) 2003 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""ExportRM

Export RelationshipManager objects from a zope database

$Id: ExportRM.py,v 1.1 2003/04/23 21:25:58 edahl Exp $"""

__version__ = "$Revision: 1.1 $"[11:-2]

import sys

import Zope
Zope.startup()

from Products.ConfUtils.ZCmdBase import ZCmdBase

from Products.RelationshipManager import RelationshipManager

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
            self.outfile.write("<objects>\n")
        if isinstance(root, RelationshipManager):
            self.outfile.write(root.exportXml()+"\n")
        for obj in root.objectValues():
            if isinstance(obj, RelationshipManager):
                self.export(obj)
        if root == self.dataroot:
            self.outfile.write("</objects>\n")


if __name__ == '__main__':
    ex = ExportRM()
    ex.export()
