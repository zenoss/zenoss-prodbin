##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


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
        if self.options.pretty:
            from pprint import pprint
            pprint(data)
        else:
            sort = False
            if self.options.jsonIndent:
                sort = True
            print(json.dumps(data, indent=self.options.jsonIndent, sort_keys=sort))


    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZenScriptBase.buildOptions(self)
        self.parser.add_option('-M', '--master',
                    dest='master',
                    default=False,
                    action='store_true',
                    help='Gather zenoss master data',
                    )

        self.parser.add_option('-p',
                    dest='pretty',
                    default=False,
                    action='store_true',
                    help='pretty print the output',
                    )
        self.parser.add_option('-i','--json_indent',
                               dest='jsonIndent',
                               help='indent setting for json output',
                               default=None,
                               type='int')

if __name__ == '__main__':
    main = Main(connect=False)
    main.run()
