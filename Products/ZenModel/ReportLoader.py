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

    def loadDatabase(self):
        reproot = self.dmd.Reports
        repdir = os.path.join(os.path.dirname(__file__),"reports")
        self.log.info("loading reports from:%s", repdir)
        for path, dirname, filenames in os.walk(repdir):
            for filename in filter(lambda f: f.endswith(".rpt"), filenames):
                fullname = os.path.join(path,filename)
                fid = filename[:-4].replace("_"," ")
                orgpath = path.replace("_", " ")
                orgpath = orgpath.split("/")
                idx = orgpath.index("reports") + 1
                orgpath = orgpath[idx:]
                orgpath = "/" + "/".join(orgpath)
                rorg = reproot.createOrganizer(orgpath)
                if getattr(rorg, fid, False): continue
                self.log.info("loading: %s %s", orgpath, filename)
                fdata = file(fullname).read()
                rpt = Report(fid, text=fdata)
                rorg._setObject(fid, rpt)
        transaction.commit()              


if __name__ == "__main__":
    rl = ReportLoader()
    rl.loadDatabase()
