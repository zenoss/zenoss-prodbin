###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import Globals
import json
from datetime import datetime
from itertools import *
from zope.interface import implements
from zope.component import getUtilitiesFor
from Products.ZenCallHome import IZenossData, IHostData, IZenossEnvData, ICallHomeCollector, IMasterCallHomeCollector
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
import logging
log = logging.getLogger("zen.callhome")


class CallHomeCollector(object):

    def __init__(self, utilityClass):
        self._utilityClass = utilityClass
        self._needsDmd = False

    def generateData(self, dmd=None):
        stats = {}
        args = []
        if self._needsDmd:
            args.append(dmd)
        for name, utilClass in getUtilitiesFor(self._utilityClass):
            log.debug("Getting data from %s %s, args: %s", name, utilClass, str(args))
            util = utilClass()
            for key, val in util.callHomeData(*args):
                log.debug("Data: %s | %s", key, val)
                if key in stats:
                    #if already a list append, else turn into a list
                    if isinstance(stats[key], list):
                        stats[key].append(val)
                    else:
                        stats[key] = [stats[key], val]
                else:
                    stats[key]=val
        return {self._key: stats}

class ZenossDataCallHomeCollector(CallHomeCollector):
    """
    Gathers data from all IZenossData utilities registered
    """
    implements(IMasterCallHomeCollector)
    def __init__(self):
        super(ZenossDataCallHomeCollector, self).__init__(IZenossData)
        self._key = "Zenoss App Data"
        self._needsDmd = True

class HostDataCallHomeCollector(CallHomeCollector):
    """
    Gathers data from all IHostData utilities registered
    """
    implements(ICallHomeCollector)
    def __init__(self):
        super(HostDataCallHomeCollector, self).__init__(IHostData)
        self._key = "Host Data"

class ZenossEnvDataCallHomeCollector(CallHomeCollector):
    """
    Gathers data from all IZenossEnvData utilities registered
    """
    implements(IMasterCallHomeCollector)
    def __init__(self):
        super(ZenossEnvDataCallHomeCollector, self).__init__(IZenossEnvData)
        self._key = "Zenoss Env Data"

class CallHomeData(object):
    def __init__(self, dmd=None, master=True ):
        self._dmd = dmd
        self._master = master

    def getData(self):
        data = dict()
        data["Report Date"] = datetime.utcnow().isoformat()
        for name, utilClass in getUtilitiesFor(ICallHomeCollector):
            chData = utilClass().generateData()
            if chData:
                data.update(chData)
        if self._master:
            for name, utilClass in getUtilitiesFor(IMasterCallHomeCollector):
                chData = utilClass().generateData(self._dmd)
                if chData:
                    data.update(chData)
        return data

    def getJsonData(self):
        return json.dumps(self.getData())

class Main(ZenScriptBase):
    def run(self):
        if self.options.master:
            log.debug("Connecting...")
            self.connect()
            log.debug("Connected")
        else:
            self.dmd = None

        chd = CallHomeData(self.dmd, self.options.master)
        data = chd.getData()
        print(json.dumps(data, indent=4))


    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZenScriptBase.buildOptions(self)
        self.parser.add_option('-M', '--master',
                    dest='master',
                    default=False,
                    action='store_true',
                    help='Gather zenoss master data',
                    )

if __name__ == '__main__':
    main = Main(connect=False)
    main.run()
