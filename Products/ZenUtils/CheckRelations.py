#################################################################
#
#   Copyright (c) 2003 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""CmdBase

Add data base access functions for command line programs

$Id: CheckRelations.py,v 1.2 2004/10/19 22:28:59 edahl Exp $"""

__version__ = "$Revision: 1.2 $"[11:-2]


import transaction

import Globals
from Acquisition import aq_parent

from Products.ZenUtils.Utils import getAllConfmonObjects

from ZCmdBase import ZCmdBase

class CheckRelations(ZCmdBase):

    def rebuild(self):
        repair = self.options.repair
        ccount = 0
        for object in getAllConfmonObjects(self.dmd):
            ccount += 1
            self.log.debug("checking relations on object %s" 
                                % object.getPrimaryDmdId())
            object.checkRelations(repair=repair)
            ch = object._p_changed
            if not ch: object._p_deactivate()
            if ccount >= self.options.savepoint:
                transaction.savepoint()
                ccount = 0
        if self.options.nocommit:
            self.log.info("not commiting any changes")
        else:
            trans = transaction.get()
            trans.note('CheckRelations cleaned relations' )
            trans.commit()


    def buildOptions(self):
        ZCmdBase.buildOptions(self)

        self.parser.add_option('-r', '--repair',
                    dest='repair', action="store_true",
                    help='repair all inconsistant relations')

        self.parser.add_option('-x', '--savepoint',
                    dest='savepoint', default=500, type="int",
                    help='how many lines should be loaded before savepoint')

        self.parser.add_option('-n', '--nocommit',
                    dest='nocommit', action="store_true",
                    help='Do not store changes to the Dmd (for debugging)')


if __name__ == "__main__":
    tmbk = CheckRelations()
    tmbk.rebuild()
