###############################################################################
#
#   Copyright (c) 2004 Zentinel Systems. 
#
#   This library is free software; you can redistribute it and/or
#   modify it under the terms of the GNU Lesser General Public
#   License as published by the Free Software Foundation; either
#   version 2.1 of the License, or (at your option) any later version.
#
###############################################################################

__doc__="""ZenTableState

Track the state of a given table.

$Id: ZenTableState.py,v 1.3 2004/01/17 04:56:13 edahl Exp $"""

__revision__ = "$Revision: 1.3 $"[11:-2]

import types

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

class ZenTableState:

    changesThatResetStart = [
        "batchSize",
        "filter",
        "sortedHeader",
        "sortedSence",
        "onlyMonitored"
        ]

    requestAtts = [
        "batchSize",
        "filter",
        "filterFields",
        "sortedHeader",
        "sortedSence",
        "sortRule",
        "start",
        "URL",
        "onlyMonitored"
        ]

    security = ClassSecurityInfo()
    #this session info isn't anything worth protecting
    security.setDefaultAccess('allow')

    def __init__(self, request, tableName, defaultBatchSize, **keys):
        self.URL = request.URL
        self.tableName = tableName
        self.sortedHeader = "primarySortKey"
        self.sortedSence="asc"
        self.sortRule = "cmp"
        self.onlyMonitored = 0
       	self.defaultBatchSize = defaultBatchSize
        self.batchSize = defaultBatchSize
        self.start = 0
        self.lastindex = 0
        self.filter = ""
        self.filterFields = []
        self.totalobjs = 0
        self.abbrStartLabel = 15
        self.abbrEndLabel = 5
        self.abbrPadding = 5
        self.abbrSeparator = ".."
        self.abbrThresh = self.abbrStartLabel + \
                        self.abbrEndLabel + self.abbrPadding
        self.tableClass = "tableheader"
        self.resetStart = False
        self.showAll = False
        self.setTableStateFromKeys(keys)


    def setTableStateFromKeys(self, keys):
        self.__dict__.update(keys)
        for key in keys.keys():
            if key not in self.requestAtts:
                self.requestAtts.append(key)


    def updateFromRequest(self, request):
        """update table state based on request"""
        if self.URL != request.URL:
            self.start=0
            self.filter = ''
        if request.get('tableName', None) != self.tableName:
            return
        for attname in self.requestAtts:
            if request.has_key(attname):
                self.setTableState(attname, request[attname])
        if not request.has_key('onlyMonitored'):
            self.setTableState('onlyMonitored', 0)
        if request.get("first",False):
            self.resetStart = True
        elif request.get("last", False):
            self.start=self.lastindex
        elif request.get("next", False):
            np = self.start + self.batchSize
            if np > self.lastindex: self.start = self.lastindex
            else: self.start = np
        elif request.get("prev", False):
            pp = self.start - self.batchSize
            if pp < 0: self.start = 0
            else: self.start = pp
        elif request.get("showAll", False):
            self.showAll = True
            # the batch size needs to be set to the total object/result count.
            # we don't have the objects here, so we will set the batchSize
            # where we do have the objects -- see buildPageNavigation() below.
        ourl = "/".join((request.URL,request.get("zenScreenName","")))
        if self.resetStart or (self.URL != request.URL and self.URL != ourl):
            self.start = 0
            self.resetStart = False


    def getPageNavigation(self):
        return self.pagenav


    def buildPageNavigation(self, objects):
        self.pagenav = []
        # this conditional is for setting the batchSize on a "showAll"
        if self.showAll:
            self.batchSize = len(objects)
            self.start = 0
            self.showAll = False
        if self.batchSize == 0:
            return self.pagenav
        lastindex=0
        for index in range(0, self.totalobjs, self.batchSize):
            pg = {}
            pg['label'] = self._pageLabel(objects, index)
            pg['index'] = index
            self.pagenav.append(pg)
            lastindex=index
        self.lastindex = lastindex


    def _pageLabel(self, objects, index):
        """make label for page navigation if field isn't sorted use page #"""
        pageLabel = ""
        if self.sortedHeader:
            pageLabel = self._buildTextLabel(objects[index])
        else:
            pageLabel = str(1+index/self.batchSize)
        return pageLabel


    def _buildTextLabel(self, item):
        startAbbr = ""
        endAbbr = ""
        attr = getattr(item, self.sortedHeader, "")
        if callable(attr): attr = attr()
        if type(attr) in types.StringTypes:
            label = attr
        else:
            label = str(attr)
        if len(label) > self.abbrThresh:
            startAbbr = label[:self.abbrStartLabel]
            if self.abbrEndLabel > 0:
                endAbbr = label[-self.abbrEndLabel:]
            label = "".join((startAbbr, self.abbrSeparator, endAbbr))
        return label


    def setTableState(self, attname, value, default=None, reset=False):
        if not hasattr(self, attname) and default != None:
            setattr(self, attname, default)
            if reset and attname not in self.changesThatResetStart:
                self.changesThatResetStart.append(attname)
            if attname not in self.requestAtts:
                self.requestAtts.append(attname)
        if value != None and getattr(self,attname, None) != value:
            setattr(self, attname, value)
            if attname in self.changesThatResetStart:
                self.resetStart = True
        return getattr(self,attname)


    def addFilterField(self, fieldName):
        """make sure we only add non-dup filterfields"""
        if fieldName and fieldName not in self.filterFields:
            self.filterFields.append(fieldName)


InitializeClass(ZenTableState)
