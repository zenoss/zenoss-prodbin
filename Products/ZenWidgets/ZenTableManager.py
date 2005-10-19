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

__doc__="""ZenTableManager

ZenTableManager is a Zope Product that helps manage and display
large sets of tabular data.  It allows for column sorting,
break down of the set into pages, and filtering of elements
in the table.  It also allows users to store their own default
page size (but publishes a hook to get this values from 
a different location).


$Id: ZenTableManager.py,v 1.4 2004/04/03 04:18:22 edahl Exp $"""

__revision__ = "$Revision: 1.4 $"[11:-2]

import re
import ZTUtils
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from OFS.SimpleItem import SimpleItem
from OFS.PropertyManager import PropertyManager
from DocumentTemplate.sequence.SortEx import sort

from ZenTableState import ZenTableState


class TableStateNotFound(Exception): pass


def manage_addZenTableManager(context, id="", REQUEST = None):
    """make a CVDeviceLoader"""
    if not id: id = "ZenTableManager"
    ztm = ZenTableManager(id)
    context._setObject(id, ztm)
    ztm = context._getOb(id)
    ztm.initTableManagerSkins()
    
    if REQUEST is not None:
        REQUEST.RESPONSE.redirect(context.absolute_url()
                                     +'/manage_main') 

class ZenTableManager(SimpleItem, PropertyManager):
    """ZenTableManager manages display of tabular data"""
    
    portal_type = meta_type = 'ZenTableManager'

    _properties = (
                    {'id':'defaultBatchSize', 'type':'int','mode':'w'}, 
                   ) 

    manage_options = (
                        PropertyManager.manage_options +
                        SimpleItem.manage_options
                     )


    def __init__(self, id):
        self.id = id
        self.defaultBatchSize = 40


    def setupTableState(self, tableName, **keys):
        """initialize or setup the session variable to track table state"""
        request = self.REQUEST
        tableStates = self.getTableStates()
        tableState = self.getTableState(tableName, **keys)
        tableState.updateFromRequest(request)
        return tableState


    def getTableState(self, tableName, attrname=None, **keys):
        """return an existing table state or a single value from the state"""
        request = self.REQUEST
        tableStates = self.getTableStates()
        tableState = tableStates.get(tableName, None)
        if not tableState:
            tableStates[tableName] = ZenTableState(request, tableName, 
                                            self.defaultBatchSize, **keys)
        if attrname == None:
            return tableStates[tableName]
        return getattr(tableState, attrname, None)


    def setTableState(self, tableName, attrname, value):
        """set the value of a table state attribute and return it"""
        tableState = self.getTableState(tableName)
        setattr(tableState, attrname, value)
        return value


    def setReqTableState(self, tableName, attrname, defaultValue):
        """set the a value in the table state from the request"""
        tableState = self.getTableState(tableName)
        value = defaultValue
        if self.REQUEST.has_key(attrname):
            value = self.REQUEST[attrname]
        self.setTableState(tableName, attrname, value)
        return value


    def getBatch(self, tableName, objects, **keys):
        """fileter, sort and batch objects and pass return set"""
        tableState = self.setupTableState(tableName, **keys) 
        if tableState.filter:
            objects = self.filterObjects(objects, tableState)
        if tableState.sortedHeader:
            objects = self.sortObjects(objects, tableState)
        tableState.buildComboBox(objects)
        if tableState.batchSize > 0:
            objects = ZTUtils.Batch(objects, tableState.batchSize,
                        start=tableState.start, orphan=0)
        return objects   
            
   
    def getTableHeader(self, tableName, fieldName, fieldTitle,
                sortRule='cmp', style='tableheader',attributes=""):
        """generate a <th></th> tag that allows column sorting"""
        href = self.getTableHeaderHref(tableName, fieldName, sortRule)
        style = self.getTableHeaderStyle(tableName, fieldName, style)
        tag = """<th class="%s" %s>""" % (style, attributes)
        tag += """<a class="%s" href="%s""" % (style, href)
        tag += fieldTitle + "</a></th>\n"
        return tag

    
    def getTableHeaderHref(self, tableName, fieldName,
                            sortRule='cmp',params=""):
        """build the href attribute for the table table headers"""

        tableState = self.getTableState(tableName)
        sortedHeader = tableState.sortedHeader
        sortedSence = tableState.sortedSence
        if sortedHeader == fieldName:
            if sortedSence == 'asc':
                sortedSence = 'desc'
            elif sortedSence == 'desc':
                fieldName = ''
                sortedSence = ''
        else:
            sortedSence = 'asc'
        href = "%s?tableName=%s&sortedHeader=%s&" % (
                self.REQUEST.URL, tableName, fieldName)
        href += "sortedSence=%s&sortRule=%s%s\">" % (
                sortedSence, sortRule, params)
        tableState.addFilterField(fieldName)
        return href
 

    def getTableHeaderStyle(self, tableName, fieldName, style):
        """apends "selected" onto the CSS style if this field is selected"""
        if self.getTableState(tableName, "sortedHeader") == fieldName:
            style = style + "selected"
        return style


    def filterObjects(self, objects, tableState):
        """filter objects base on a regex in filter and list of fields
        in filterFields.  If negateFilter is selected the regex is negated"""
        if tableState.filterFields:
            filterFields = tableState.filterFields
        else:
            filterFields = ('getId',)
        negateFilter = tableState.negateFilter
        filter = re.compile(tableState.filter).search
        filteredObjects = []
        for obj in objects:
            target = []
            for field in filterFields:
                value = getattr(obj, field, None)
                if callable(value):
                    value = value()
                target.append(str(value))
            targetstring = " ".join(target)
            fvalue =  filter(targetstring)
            if (fvalue and not negateFilter) or (not fvalue and negateFilter):
                filteredObjects.append(obj)
        return filteredObjects  


    def sortObjects(self, objects, tableState):
        """sort objects based on current sortedHeader, rule and sence"""
        sortOn = (( tableState.sortedHeader, 
                    tableState.sortRule, 
                    tableState.sortedSence),)
        return sort(objects, sortOn)


    def getTableNavigation(self, context, tableName, batch):
        """generate the navigation links for bar at bottom of table"""
        tableState = self.getTableState(tableName)
        url = context.absolute_url_path()
        navbar = "\n"
        if tableState.batchSize==0: return navbar
        if tableState.start != 0 and tableState.totalobjs:
            navbar += self._navLink(url, tableName, "First", 
                            0, tableState.negateFilter)
            navbar += self._navLink(url, tableName, "Prev",
                            batch.previous.first, tableState.negateFilter)
        else:
            navbar += "First Previous\n"
        navbar += tableState.getComboBox()
        if batch.next:
            navbar += self._navLink(url, tableName, "Next",
                            batch.next.first, tableState.negateFilter)
            navbar += self._navLink(url, tableName, "Last", 
                            tableState.lastindex, tableState.negateFilter)
        else:
            navbar += "Next Last"
        return navbar + "\n"
 

    def _navLink(self, url, tableName, label, start, negateFilter):
        link = """<a href="%s?tableName=%s&start:int=%d""" % (
                    url, tableName, start)
        if negateFilter: link += "&negateFilter=1"
        link += "\">%s</a> " % label
        return link


    def getTableStates(self):
        session = self.REQUEST.SESSION
        if not session.has_key('zentablestates'):
            session['zentablestates'] = {}
        return session['zentablestates']


    def tableStatesHasTable(self, tableName):
        return self.getTableStates().has_key(tableName)


    def initTableManagerSkins(self):
        """setup the skins that come with ZenTableManager"""
        try:
            import string 
            from Products.CMFCore.utils import getToolByName
            from Products.CMFCore.DirectoryView import addDirectoryViews
            skinstool = getToolByName(self, 'portal_skins') 
            if 'zentablemanager' not in skinstool.objectIds():
                addDirectoryViews(skinstool, 'skins', globals())
            skins = skinstool.getSkinSelections()
            for skin in skins:
                path = skinstool.getSkinPath(skin)
                path = map(string.strip, string.split(path,','))
                if 'zentablemanager' not in path:
                    path.append('zentablemanager')
                    path = string.join(path, ', ')
                    skinstool.addSkinSelection(skin, path)
        except ImportError, e:
            if "Products.CMFCore.utils" in e.args: pass
            else: raise
        except AttributeError, e:
            if "portal_skin" in e.args: pass
            else: raise

    
InitializeClass(ZenTableManager)
