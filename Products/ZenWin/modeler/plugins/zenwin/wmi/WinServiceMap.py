###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Products.ZenWin.WMIPlugin import WMIPlugin
from Products.ZenUtils.Utils import prepId

class WinServiceMap(WMIPlugin):

    maptype = "WinServiceMap"
    compname = "os"
    relname = "winservices"
    modname = "Products.ZenModel.WinService"
    
    attrs = ("acceptPause","acceptStop","name","caption",
         "pathName","serviceType","startMode","startName")

    queryMap = {
     "Win32_Service":"Select %s From Win32_Service" % (",".join(attrs)),
    }
        
    def queries(self):
        return self.queryMap
        
    def process(self, device, results, log):
        """
        Collect win service info from this device.
        """
        log.info('Processing WinServices for device %s' % device.id)
        
        rm = self.relMap()
        for svc in results["Win32_Service"]:
            om = self.objectMap()
            om.id = prepId(svc.name)
            om.setServiceClass = {'name':svc.name, 'description':svc.caption}
            for att in self.attrs:
                if att in ("name", "caption"): continue
                setattr(om, att, getattr(svc, att, ""))
            rm.append(om)
        return rm

