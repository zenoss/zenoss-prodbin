#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################
import os
import transaction
import Globals

from Products.ZenRelations.ImportRM import ImportRM

class XmlDataLoader(ImportRM):

    def loadDatabase(self):
        datadir = os.path.join(os.path.dirname(__file__),"data")
        self.log.info("loading data from:%s", datadir)
        for path, dirname, filenames in os.walk(datadir):
            for filename in filter(lambda f: f.endswith(".xml"), filenames):
                self.options.infile = os.path.join(path,filename)
                self.log.info("loading: %s", self.options.infile)
                ImportRM.loadDatabase(self)
        # Reindex ProductKeys and EventClassKeys after XML load
        self.dmd.Manufacturers.reIndex()
        self.dmd.Events.reIndex()
        transaction.commit()


if __name__ == "__main__":
    rl = XmlDataLoader()
    rl.loadDatabase()
