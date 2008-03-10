###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import Globals
from WMIC import WMIClient
from ProcessProxy import Record

def picklable(item):
    obj = Record() 
    for prop in item.Properties_.set.keys():
        setattr(obj, prop, getattr(item, prop))
    return obj
    

def picklableResults(results):
    ret = {}
    for k, v in results.items():
        values = []
        for item in v:
            values.append(picklable(item))
        ret[k] = values
    return ret


class Query:

    def __init__(self, device):
        self.wmic = WMIClient(device)
        self.wmic.connect()

    def query(self, queries):
        return picklableResults(self.wmic.query(queries))

