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
__doc__='''

Change zNmapPortscanOptions to new format without ";", 
allowing Tales expressions

'''
import Migrate
from Acquisition import aq_base
from Products.ZenModel.DeviceClass import DeviceClass
import logging
log = logging.getLogger("zen.migrate")

class zNmapPortscanOptions(Migrate.Step):
    version = Migrate.Version(2, 5, 70)

    #try to migrate any other properties that still contain ";" instead of " "
    def _tryMigrate(self, path, dmd):
        obj = dmd.getObjByPath('/zport/dmd/Devices%s' % path)
        if not obj: return
        oldopts = obj.zNmapPortscanOptions
        if oldopts.find("${here/") > -1: return
        newopts = oldopts.replace(";", " ")
        newopts += " ${here/manageIp}"
        log.debug("replacing zNmapPortscanOptions at %s from '%s' to '%s'" % (path, oldopts, newopts))
        obj._updateProperty("zNmapPortscanOptions", newopts)


    def cutover(self, dmd):
        try:
            #in case the property doesn't exist (unlikely)
            if not hasattr(aq_base(dmd.Devices), 'zNmapPortscanOptions'):
                    log.info("creating zNmapOptions")
                    dmd.Devices._setProperty("zNmapPortscanOptions", 
                                     "-p 1-1024 -sT --open -oG - ${here/manageIp}")

            #take care of all others
            ppaths = []
            for d in dmd.Devices.getSubDevices():
                ppath = d.zenPropertyPath("zNmapPortscanOptions")
                if not ppath in ppaths:
                    ppaths.append(ppath)
                    self._tryMigrate(ppath, dmd)
        except Exception, e:
            log.error(str(e))
            pass 

zNmapPortscanOptions()
