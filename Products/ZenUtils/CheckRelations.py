#################################################################
#
#   Copyright (c) 2003 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""CmdBase

Add data base access functions for command line programs

$Id: CheckRelations.py,v 1.2 2004/10/19 22:28:59 edahl Exp $"""

__version__ = "$Revision: 1.2 $"[11:-2]

import gc

import Globals
from Acquisition import aq_parent

from Products.ZenUtils.Utils import getAllConfmonObjects
from Products.Confmon.Classification import Classification
from Products.Confmon.Instance import Instance

from ZCmdBase import ZCmdBase

class CheckRelations(ZCmdBase):

    def rebuild(self):
        repair = self.options.repair
        ccount = 0
        for object in getAllConfmonObjects(self.dmd):
            ccount += 1
            self.log.debug("checking relations on object %s" 
                                % object.getPrimaryFullId())
            object.checkRelations(repair=repair,log=self.log)
            if ccount >= self.options.commitCount and not self.options.noCommit:
                trans = get_transaction()
                trans.note('CheckRelations cleaned relations')
                trans.commit()
                ccount = 0
                gc.collect()
        if self.options.noCommit:
            self.log.info("not commiting any changes")
        else:
            trans = get_transaction()
            trans.note('CheckRelations cleaned relations' )
            trans.commit()


    def buildOptions(self):
        ZCmdBase.buildOptions(self)

        self.parser.add_option('-r', '--repair',
                    dest='repair',
                    default=False,
                    action="store_true",
                    help='repair all inconsistant relations')

        self.parser.add_option('-x', '--commitCount',
                    dest='commitCount',
                    default=20,
                    type="int",
                    help='how many lines should be loaded before commit')

        self.parser.add_option('-n', '--noCommit',
                    dest='noCommit',
                    action="store_true",
                    default=0,
                    help='Do not store changes to the Dmd (for debugging)')


if __name__ == "__main__":
    tmbk = CheckRelations()
    tmbk.rebuild()
