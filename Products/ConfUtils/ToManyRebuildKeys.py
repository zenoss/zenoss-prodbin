#################################################################
#
#   Copyright (c) 2003 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""CmdBase

Add data base access functions for command line programs

$Id: ToManyRebuildKeys.py,v 1.2 2003/11/12 22:05:48 edahl Exp $"""

__version__ = "$Revision: 1.2 $"[11:-2]

from Acquisition import aq_parent

from Products.ZenUtils.Utils import getSubObjects

from ZCmdBase import ZCmdBase

class ToManyRebuildKeys(ZCmdBase):

    def rebuild(self):
        tomanys = getSubObjects(self.dmd, self.filter, self.decend)
        ccount = 0
        for tomany in tomanys:
            self.log.debug("rebuilding keys for relation %s on object %s" %
                                (tomany.getId(), aq_parent(tomany).getId()))
            ccount += tomany.rebuildKeys(self.log)
            if ccount >= self.options.commitCount and not self.options.noCommit:
                trans = get_transaction()
                trans.note('ToManyRebuildKeys rebuilt keys')
                trans.commit()
                ccount = 0
        if self.options.noCommit:
            self.log.info("not commiting any changes")
        else:
            trans = get_transaction()
            trans.note('ToManyRebuildKeys rebuilt keys')
            trans.commit()


    def filter(self, obj):
        return obj.meta_type == "To Many Relationship"


    def decend(self, obj):
        from Products.Confmon.Classification import Classification
        from Products.Confmon.Instance import Instance
        from Products.ZenRelations.ToManyRelationship import ToManyRelationship
        return (isinstance(obj, Classification) or 
                isinstance(obj, Instance) or
                isinstance(obj, ToManyRelationship))


    def buildOptions(self):
        ZCmdBase.buildOptions(self)
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
    tmbk = ToManyRebuildKeys()
    tmbk.rebuild()
