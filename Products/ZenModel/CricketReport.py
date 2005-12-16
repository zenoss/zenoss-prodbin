################################################################
#
#   Copyright (c) 2002 Cablevision Corporation. All rights reserved.
#
#################################################################

__doc__="""CricketReport

$Id: CricketReport.py,v 1.1.1.1 2004/10/14 20:55:29 edahl Exp $"""

__version__ = "$Revision: 1.1.1.1 $"[11:-2]

import pprint

from Globals import DTMLFile
from Globals import InitializeClass

from zLOG import LOG, INFO

from AccessControl import ClassSecurityInfo
from OFS.SimpleItem import SimpleItem


from Products.ZenModel.ZenModelBase import ZenModelBase

def manage_addCricketReport(context, id, REQUEST = None):
    """make a CricketReport"""
    d = CricketReport(id)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addCricketReport = DTMLFile('dtml/addCricketReport',globals())

class CricketReport(SimpleItem, ZenModelBase):

    meta_type = 'CricketReport'

    def collectData(self, devicepath, dsidx, drange):
        """Return data for the CricketReport for all devices under devicepath.
        """
        dc = self.getDmdRoot("Devices").getOrganizer(devicepath)
        CricketDatas = []
        devices = dc.getSubDevices()
        for device in devices:
            crconf = device.cricket()
            if not crconf: continue
            crpath = device.cricketTargetPath()
            if not crpath: continue
            CricketDatas.append(CricketData(device.getId(), 
                            device.getModelName(),
                            device.getPrimaryUrlPath(),
                            crpath, crconf))
        data = self.callCricket(CricketDatas, dsidx, drange) 
        return data


    def callCricket(self, CricketDatas, dsidx, drange):
        """group rhdatas by common cricket servers
        build the total rrd command and send out to cricket server
        then fill rhdatas will proper return values"""
        cricketconfs = {}
        for CricketData in CricketDatas:
            if not cricketconfs.has_key(CricketData.cricketconf):
                cricketconfs[CricketData.cricketconf] = []
            cricketconfs[CricketData.cricketconf].append(CricketData)

        scount = 0
        for cricketconf, crCricketDatas in cricketconfs.items():
            gopts = []
            for CricketData in crCricketDatas:
                gopts.extend(CricketData.getOpts(scount,dsidx))
                scount += 1
            #pprint.pprint(gopts)
            cricketdata = cricketconf.cricketCustomSummary(gopts, drange)
            for i in range(0,len(crCricketDatas)):
                j = i * 2
                CricketData = crCricketDatas[i]
                try:
                    CricketData.dataavg = float(cricketdata[j])
                    CricketData.datamax = float(cricketdata[j+1])
                except TypeError: pass
        CricketDatas = filter(lambda x: x.dataavg,CricketDatas)
        return CricketDatas
            


InitializeClass(CricketReport)


class CricketData:
    """hold cricet data"""
    
    security = ClassSecurityInfo()
    security.setDefaultAccess('allow')


    def __init__(self, devicename, devicemodel, deviceurl, 
                    cricketpath, cricketconf, 
                    dataavg=None, datamax=None):
        self.devicename = devicename
        self.devicemodel = devicemodel
        self.deviceurl = deviceurl
        self.cricketpath = cricketpath + "/" + devicename
        self.cricketconf = cricketconf
        self.dataavg = dataavg
        self.datamax = datamax


    def getOpts(self, scount, dsidx):
        gopts = []
        src = 'v%d' % scount
        gopts.append("DEF:%s=%s.rrd:%s:AVERAGE" % (src,self.cricketpath,dsidx))
        #PRINT statements
        gopts.append("PRINT:%s:AVERAGE:%%.2lf" % src)
        gopts.append("PRINT:%s:MAX:%%.2lf" % src)
        return gopts
    

InitializeClass(CricketData)
