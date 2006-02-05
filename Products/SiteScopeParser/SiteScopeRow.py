#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

"""SiteScopeRow

Represents one parsed row of a SiteScope Page

$Id: SiteScopeRow.py,v 1.17 2002/11/08 18:03:40 edahl Exp $"""

__version__ = "$Revision: 1.17 $"[11:-2]

from Acquisition import Explicit
from AccessControl import ClassSecurityInfo
from AccessControl import getSecurityManager
from Globals import InitializeClass


class SiteScopeRow(Explicit):

    condition = {'nodata':'misc_/SiteScopeParser/magentaball_img',
                'error' : 'misc_/SiteScopeParser/redball_img',
                'good' : 'misc_/SiteScopeParser/greenball_img',
                'warning' : 'misc_/SiteScopeParser/yellowball_img', }

    security = ClassSecurityInfo()
    security.declareObjectPublic()

    def __init__(self, row, request=None):
        self._row = row
        if request:
            self.myUrl = request['URL']
        else:
            self.myUrl = ""
    

    def isNamed(self,name):
        retval = 0
        if self._row['Name']['Data'] == name:
            retval = 1
        return retval


    def columns(self):
        retdict = {}
        for key in self._row.keys():
            retdict[key] = self._getValue(key) 
        return retdict


    def fixURLs(self, host, base):
        row = self._row
        for key in row.keys():
            if row[key].has_key('Href'):
                if row[key]['Href'][:1] == '/':
                    row[key]['Href'] = ('http://' + host +
                        row[key]['Href'])
                else:
                    row[key]['Href'] = ("http://" + base +
                        row[key]['Href'])

    security.declarePublic('Edit')
    def Edit(self):
        return self._getValue('Edit')

    security.declarePublic('Del')
    def Del(self):
        return self._getValue('Del')
    
    security.declarePublic('Name')
    def Name(self):
        return self._getValue('Name')

    security.declarePublic('NameUrl')
    def NameUrl(self):
        return self._getValue('Name', 1)

    security.declarePublic('NameAutoUrl')
    def NameAutoUrl(self):
        url = None
        refUrl = self.NameUrl()
        if refUrl.find("go.exe") > 0 or self.Condition() == 'nodata':
            url = refUrl 
        else:
            url = self.myUrl + "?refUrl=%22" + refUrl + "%22"
        return url 

    security.declarePublic('Condition')
    def Condition(self):
        user = getSecurityManager().getUser()
        if not user.has_role('Manager'):
            return 'nodata'
        return self._getValue('Condition')
    
    security.declarePublic('ConditionUrl')
    def ConditionUrl(self):
        return self._getValue('Condition',1)

    security.declarePublic('ConditionImg')
    def ConditionImg(self):
        col = self._row.get('Condition', None)
        if col == None: col = self._row.get('State')
        data = col['Data']
        if data.find('good') > -1: data = "good"
        elif data.find('error') > -1: data = "error"
        elif data.find('warn') > -1: data = "warning"
        else: data = "nodata"
        img = ("""<img alt="%s" src="%s" border="0">""" 
                    % (col['Data'],
                    self.condition[data]))
        return img 


    security.declarePublic('More')
    def More(self):
        if self._row.has_key('More'):
            return self._getValue('More')

    security.declarePublic('MoreUrl')
    def MoreUrl(self):
        if self._row.has_key('More'):
            return self._getValue('More',1)

    security.declarePublic('Ack')
    def Ack(self):
        if self._row.has_key('Ack'):
            return self._getValue('Ack')

    security.declarePublic('AckUrl')
    def AckUrl(self):
        if self._row.has_key('Ack'):
            return self._getValue('Ack',1)

    security.declarePublic('Refresh')
    def Refresh(self):
        if self._row.has_key('Refresh'):
            return self._getValue('Refresh')

    security.declarePublic('RefreshUrl')
    def RefreshUrl(self):
        if self._row.has_key('Refresh'):
            return self._getValue('Refresh',1)

    security.declarePublic('Gauge')
    def Gauge(self):
        if self._row.has_key('Gauge'):
            return self._getValue('Gauge')

    security.declarePublic('GaugeUrl')
    def GaugeUrl(self):
        if self._row.has_key('Gauge'):
            return self._getValue('Gauge',1)

    security.declarePublic('Updated')
    def Updated(self):
        if self._row.has_key('Updated'):
            return self._getValue('Updated')

    security.declarePublic('UpdatedUrl')
    def UpdatedUrl(self):
        if self._row.has_key('Updated'):
            return self._getValue('Updated',1)

    security.declarePublic('Status')
    def Status(self):
        if self._row.has_key('Status'):
            return self._getValue('Status')

    security.declarePublic('StatusUrl')
    def StatusUrl(self):
        if self._row.has_key('Status'):
            return self._getValue('Status',1)

    def _getValue(self, column, href=0):
        retval = ''
        if self._row.has_key(column):
            col = self._row[column] 
            if href and col.has_key('Href'):
                retval = col['Href']
            elif col.has_key('Data'):
                retval = col['Data']
        return retval


InitializeClass(SiteScopeRow)
