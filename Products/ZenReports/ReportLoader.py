#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################
import os
import transaction
import Globals

from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenModel.Report import Report

class ReportLoader(ZCmdBase):

    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('-f', '--force', dest='force', 
                               action='store_true', default=0,
                               help="Force load all the reports")

    def loadDatabase(self):
        repdir = os.path.join(os.path.dirname(__file__),"reports")
        self.loadDirectory(repdir)
        transaction.commit()

    def reports(self, directory):
        def normalize(f):
            return f.replace("_", " ")
        def toOrg(path):
            path = normalize(path).split("/")
            path = path[path.index("reports") + 1:]
            return "/" + "/".join(path)
        return [(toOrg(p), normalize(f[:-4]), os.path.join(p, f))
                for p, ds, fs in os.walk(directory)
                for f in fs
                if f.endswith(".rpt")]

    def unloadDirectory(self, repdir):
        self.log.info("removing reports from:%s", repdir)
        reproot = self.dmd.Reports
        for orgpath, fid, fullname in self.reports(repdir):
            rorg = reproot.createOrganizer(orgpath)
            if getattr(rorg, fid, False):
                rorg._delObject(fid)
            while rorg.id != 'Reports':
                if not rorg.objectValues():
                    id = rorg.id
                    rorg = rorg.getPrimaryParent()
                    rorg._delObject(id)
        

    def loadDirectory(self, repdir):
        self.log.info("loading reports from:%s", repdir)
        reproot = self.dmd.Reports
        for orgpath, fid, fullname in self.reports(repdir):
            rorg = reproot.createOrganizer(orgpath)
            if getattr(rorg, fid, False):
                if self.options.force:
                    rorg._delObject(fid)
                else:
                    continue
            self.log.info("loading: %s/%s", orgpath, fid)
            fdata = file(fullname).read()
            rpt = Report(fid, text=fdata)
            rorg._setObject(fid, rpt)


if __name__ == "__main__":
    rl = ReportLoader()
    rl.loadDatabase()
