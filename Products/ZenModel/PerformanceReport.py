################################################################
#
#   Copyright (c) 2002 Cablevision Corporation. All rights reserved.
#
#################################################################
import warnings
warnings.warn("PerformanceReport is deprecated", DeprecationWarning)

__doc__="""PerformanceReport

$Id: PerformanceReport.py,v 1.1.1.1 2004/10/14 20:55:29 edahl Exp $"""

__version__ = "$Revision: 1.1.1.1 $"[11:-2]

import logging
log = logging.getLogger("zen.Cricket")

from Globals import DTMLFile
from Globals import InitializeClass

from zLOG import LOG, INFO

from AccessControl import ClassSecurityInfo
from OFS.SimpleItem import SimpleItem


from Products.ZenModel.ZenModelBase import ZenModelBase
from Products.ZenModel.PerformanceConf import performancePath

def manage_addPerformanceReport(context, REQUEST = None):
    """make a PerformanceReport"""
    id = "PerformanceReport"
    d = PerformanceReport(id)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

#addPerformanceReport = DTMLFile('dtml/addPerformanceReport',globals())

class PerformanceReport(SimpleItem, ZenModelBase):

    meta_type = 'PerformanceReport'

    def collectData(self, devicepath, dsidx, drange):
        """Return data for the PerformanceReport for all devices under devicepath.
        """
        dc = self.getDmdRoot("Devices").getOrganizer(devicepath)
        PerformanceDatas = []
        devices = dc.getSubDevices()
        for device in devices:
            perf = device.perfServer()
            if not perf: continue
            PerformanceDatas.append(PerformanceData(device.getId(), 
                            device.getDeviceClassPath(),
                            device.getPrimaryUrlPath(),
                            perf))
        data = self.callRRD(PerformanceDatas, dsidx, drange) 
        return data


    def callRRD(self, PerformanceDatas, dsidx, drange):
        """group rhdatas by common performance servers
        build the total rrd command and send out to the server
        then fill rhdatas will proper return values"""
        confs = {}
        for PerformanceData in PerformanceDatas:
            if not confs.has_key(PerformanceData.conf):
                confs[PerformanceData.conf] = []
            confs[PerformanceData.conf].append(PerformanceData)

        scount = 0
        for conf, crPerformanceDatas in confs.items():
            gopts = []
            for PerformanceData in crPerformanceDatas:
                gopts.extend(PerformanceData.getOpts(scount,dsidx))
                scount += 1
            #pprint.pprint(gopts)
            perfdata = conf.performanceCustomSummary(gopts, drange)
            for i in range(0,len(crPerformanceDatas)):
                j = i * 2
                PerformanceData = crPerformanceDatas[i]
                try:
                    PerformanceData.dataavg = float(perfdata[j])
                    PerformanceData.datamax = float(perfdata[j+1])
                except TypeError: pass
        PerformanceDatas = filter(lambda x: x.dataavg,PerformanceDatas)
        return PerformanceDatas
            


InitializeClass(PerformanceReport)


class PerformanceData:
    """hold cricet data"""
    
    security = ClassSecurityInfo()
    security.setDefaultAccess('allow')


    def __init__(self, devicename, devicepath, deviceurl, 
                    conf, 
                    dataavg=None, datamax=None):
        self.devicename = devicename
        self.devicepath = devicepath
        self.deviceurl = deviceurl
        self.conf = conf
        self.dataavg = dataavg
        self.datamax = datamax


    def getOpts(self, scount, dsidx):
        gopts = []
        src = 'v%d' % scount
        gopts.append("DEF:%s=%s.rrd:%s:AVERAGE" % (src,
                                                   performancePath(self.devicename),
                                                   dsidx))
        #PRINT statements
        gopts.append("PRINT:%s:AVERAGE:%%.2lf" % src)
        gopts.append("PRINT:%s:MAX:%%.2lf" % src)
        return gopts
    

InitializeClass(PerformanceData)
