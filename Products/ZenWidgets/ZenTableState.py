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

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

class ZenTableState:

    changesThatResetStart = ("batchSize", "filter", 
                            "negateFilter", "sortedHeader", "sortedSence")

    security = ClassSecurityInfo()
    #this session info isn't anything worth protecting
    security.setDefaultAccess('allow') 

    def __init__(self, request, tableName, **keys):
        self.url = request.URL
        self.tableName = tableName
        self.sortedHeader = "primarySortKey"
        self.sortedSence="asc"
        self.sortRule = "cmp"
        self.batchSize = 40
        self.start = 0
        self.filter = ""
        self.filterFields = []
        self.negateFilter = 0
        self.totalobjs = 0
        self.abbrStartLabel = 15
        self.abbrEndLabel = 5
        self.abbrPadding = 5
        self.abbrSeparator = ".."
        self.abbrThresh = self.abbrStartLabel + \
                        self.abbrEndLabel + self.abbrPadding
        self.tableClass = "tableheader"

        self.comboBox = ""  
        # do we really need to protect the state like this??
        for k, v in keys.items():
            if hasattr(self, k):
                setattr(self, k, v)
        #self.__dict__.update(keys)


    def updateFromRequest(self, request):
        """update table state based on request request"""
        startReset = 0
        if (request.has_key('tableName') 
            and request['tableName'] == self.tableName):
            for attname in self.__dict__.keys():
                if (request.has_key(attname) and 
                    getattr(self,attname) != request[attname]):
                    setattr(self,attname, request[attname])
                    if attname in self.changesThatResetStart: 
                        startReset = 1
            if (not request.has_key("negateFilter") 
                and self.negateFilter):
                self.negateFilter = 0
                startReset = 1
            if startReset: self.start = 0
            if not self.filter:
                self.negateFilter = 0


    def addFilterField(self, fieldName):
        """make sure we only add non-dup filterfields"""
        if fieldName and fieldName not in self.filterFields:
            self.filterFields.append(fieldName)


    def getComboBox(self):
        return self.comboBox


    def buildComboBox(self, objects):
        """make labels for the combo that show the names of items"""
        if self.batchSize == 0: 
            self.comboBox = ""
            return
        self.totalobjs = len(objects)
        clines = []
        cline = """<select class="%s" name="start:int" """ % self.tableClass
        cline += """onchange="this.form.submit()">\n"""
        lastindex=0
        for index in range(0, self.totalobjs, self.batchSize):
            pageLabel = self._pageLabel(objects, index)
            cline += "<option "
            if self.start == index: cline += "selected "
            cline += """value="%d">%s</option>\n""" % (index, pageLabel)
            lastindex=index
        cline += """</select>\n"""
        clines.append(cline)
        self.lastindex = lastindex
        self.comboBox = "".join(clines)


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
        label = str(attr)
        if len(label) > self.abbrThresh:
            startAbbr = label[:self.abbrStartLabel]
            if self.abbrEndLabel > 0:
                endAbbr = label[-self.abbrEndLabel:]
            label = "".join((startAbbr, self.abbrSeparator, endAbbr))
        return label


InitializeClass(ZenTableState)
