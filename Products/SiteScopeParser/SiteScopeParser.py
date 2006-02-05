#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

"""SiteScopeParser

A class for parsing SiteScope's HTML output and creating
a dictionary based data structure from it.

$Id: SiteScopeParser.py,v 1.11 2002/11/07 21:37:45 edahl Exp $"""

__version__ = "$Revision: 1.11 $"[11:-2]

from SiteScopeRow import SiteScopeRow
from ParsedData import ParsedData
from htmllib import HTMLParser
from formatter import NullFormatter
from Acquisition import Explicit
import pprint
import urllib

class SiteScopeParser(HTMLParser):
    "A class to grok SiteScope secondary pages"

    def __init__(self,request=None,formatter=NullFormatter()):
        "Build object, initialize values"

        HTMLParser.__init__(self,formatter)
        self.request = request
        self._tagDataProc = ""
        self._columns = []
        self._results = [] 
        self._inrow = 0


    def start_th(self,attrs):
        "Set the tag data function for TH tags"

        self._tagDataProc = self._handleDataForTh


    def end_th(self):
        "Null the tag data processing function"

        self._tagDataProc = ''


    def start_tr(self,attrs):
        '''Handle the beginning of TR sets,
        which are considered rows of data'''

        # self._inrow prevents multiple entry
        if self._columns and self._inrow == 0:
            self._inrow = 1
            self._tagDataProc = self._handleOtherData
            self._row = {}
            for colname in self._columns:
                self._row[colname]={}
            self.numtds = 0


    def end_tr(self):
        '''Handle the end of a TR set,
        append the content of the row to
        the result list'''

        # self._inrow prevents multiple entry
        if self._columns and self._inrow == 1:
            self._inrow = 0
            
            name = None
            if self._row.has_key('Name'):
                if self._row['Name'].has_key('Data'):
                    name = self._row['Name']['Data']
            if name:
                self._results.append(
                    SiteScopeRow(self._row, self.request))
            self._tagDataProc = ''


    def start_td(self,attrs):
        "Set the tag data function to handle TDs"

        self._tagDataProc = self._handleOtherData


    def end_td(self):
        '''Increment the number of TD tags seen
        so that we use the proper column name'''

        if self._columns:
            self.numtds+=1


    def start_a(self,attrs):
        "Extract the URL from an anchor tag"

        if self._columns:
            self._tagDataProc = self._handleOtherData
            self._row[
                self._columns[
                    self.numtds]]['Href'] = self._getAttr(attrs,'href')

    
    def end_a(self):
        "Null the tag data processing function"

        self._tagDataProc = ''


    def start_img(self,attrs):
        '''Process an img tag, finding the
        row's status in the alt property'''

        if self._columns:
            #self._tagDataProc = 'img'
            self._row[
                self._columns[
                    self.numtds]]['Data'] = self._getAttr(attrs,'alt')


    def start_table(self,attrs):
        "Necesarry for end_table()"

        pass


    def end_table(self):
        "Null column list"
        
        self._columns=[]


    def handle_data(self,data):
        '''Call the tag data processing function,
        if available'''

        if self._tagDataProc:
            self._tagDataProc(data)

    
    def _handleDataForTh(self,data):
        "Build a list of column names"

        col=data
        if col == '\xa0':
            col = 'Condition'
        self._columns.append(col)


    def _handleOtherData(self,data):
        '''Handle all data that needs to be inserted
        into the parents tag's Data element of the
        dictionary'''

        if self._columns:
            self._row[
                self._columns[
                    self.numtds]]['Data'] = data


    def _getAttr(self,attrs,name):
        '''Get a value from an attribute hash passed
        to a tag function'''

        attrval = ''
        for key,val in attrs:
            if key == name:
                attrval = val
        return attrval


    def feed(self, file):
        '''Override the superclass's feed method to prevent
        compounding all of our data'''

        self._columns = []
        self._results = []
        HTMLParser.feed(self,file)


    def getResults(self):
        "Return the parse tree"

        return ParsedData(tuple(self._results))


class SiteScopeFirstParser(HTMLParser):
    "A class to grok SiteScope's first page"
    
    def __init__(self, request, formatter=NullFormatter()):
        "Build object and initialize members"

        HTMLParser.__init__(self,formatter)
        self.request = request
        self._ds = []
        self._current_status = ''


    def start_img(self,attrs):
        "Look for status in IMG tags alt property"

        codes = ('error','E','warning','W','good','g')
        for key,val in attrs:
            if key == 'alt':
                if val in codes:
                    self._current_status = val


    def start_a(self,attrs):
        '''Process an anchor tag,
        which marks the end of a row
        of data. The contents of the
        row are appended to the results'''

        current_href = ''
        for key, val in attrs:
            if key == 'href':
                current_href = val
            elif key == 'title':
                current_title = val
                self._ds.append(
                    SiteScopeRow({
                        'Name':     {
                            'Data': current_title,
                            'Href': current_href,
                            },
                        'Condition':    {
                            'Data': self._current_status,
                            }},
                            self.request))


    def feed(self, file):
        "Override superclass so we don't lose data"

        self._ds = []
        self._current_status = ''
        HTMLParser.feed(self, file)

        
    def getResults(self):
        "Return the result list"

        return ParsedData(tuple(self._ds))


if __name__=="__main__":
    x=SiteScopeParser()
    x.feed(open("html/DetailDNS.html").read())
    x.close()
    pprint.pprint(x.getResults())
