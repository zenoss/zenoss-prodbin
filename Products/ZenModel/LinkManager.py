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


from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import getSecurityManager
from AccessControl import Permissions as permissions

from sets import Set

import Products.ZenUtils.guid as guid
from Products.AdvancedQuery import MatchRegexp, Or, In, Eq

import simplejson

from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.Search import makeCaseInsensitiveFieldIndex
from Products.ZenUtils.Search import makeCaseInsensitiveKeywordIndex

from Products.ZenModel.Link import Link
from Products.ZenModel.Linkable import Linkable


def manage_addLinkManager(context, id=None):
    """ Make a LinkManager """
    if not id:
        id = "ZenLinkManager"
    mgr = LinkManager(id)
    context._setObject(mgr.id, mgr)
    mgr = context._getOb(id)
    mgr.createCatalog()
    mgr.buildRelations()


class LinkManager(ZenModelRM):
    """ An object that manages links.
    """

    default_catalog = "linkSearch"

    _properties = (
        {'id':'link_type','type':'string','mode':'w'},
        {'id':'OSI_layer', 'type':'int', 'mode':'w'},
        {'id':'entry_type', 'type':'string', 'mode':'w'},
    )

    _relations = (
        ("links", ToManyCont(ToOne, "Products.ZenModel.Link", "linkManager")),
    )

    factory_type_information = (
        { 'immediate_view' : 'viewLinkManager',
          'factory'        : 'manage_addLinkManager',
          'actions'        : (
           { 'id'            : 'viewLinkManager'
           , 'name'          : 'Link Manager'
           , 'action'        : 'viewLinkManager'
           , 'permissions'   : ( "Manage DMD", )
           },)
        },
    )

    security = ClassSecurityInfo()

    def __init__(self, id):
        self.id = id

    def createCatalog(self):
        """ Creates the catalog for link searching """

        from Products.ZCatalog.ZCatalog import manage_addZCatalog

        manage_addZCatalog(self, self.default_catalog,
            self.default_catalog)
        zcat = self._getOb(self.default_catalog)
        cat = zcat._catalog
        for idxname in ['link_type','OSI_layer']:
            cat.addIndex(idxname, 
                makeCaseInsensitiveFieldIndex(idxname, 'string'))
        cat.addIndex('getEndpointNames',
            makeCaseInsensitiveKeywordIndex('getEndpointNames'))
        zcat.addColumn('id')

    def _getCatalog(self):
        """ Return the ZCatalog under the default_catalog attribute """
        return getattr(self, self.default_catalog, None)

    security.declareProtected('Change Device', 'manage_addLink')
    def manage_addLink(self, pointa, pointb,
                       link_type="", OSI_layer="1",
                       entry_type="manual", REQUEST=None):
        """ Add a link """
        newid = guid.generate()
        link = Link(newid)
        link.setEndpoints(pointa, pointb)

        self.links._setObject(newid, link)
        if REQUEST:
            return self.callZenScreen(REQUEST)
        return link

    security.declareProtected('Change Device', 'manage_removeLink')
    def manage_removeLink(self, linkid, REQUEST=None):
        """ Delete a link """
        self.links._delObject(linkid)
        if REQUEST:
            return self.callZenScreen(REQUEST)

    security.declareProtected('Change Device', 'getNodeLinks')
    def getNodeLinks(self, node):
        """ Returns all links associated with a given Linkable """
        try:
            return node.links.objectValuesGen()
        except AttributeError:
            return node.getLinks(recursive=False)

    security.declareProtected('View', 'getLinkedNodes')
    def getLinkedNodes(self, node):
        """ Returns all nodes linked to a given Linkable """
        nlinks = self.getNodeLinks(node)
        return map(lambda x:x.getOtherEndpoint(node), nlinks)

    def query_catalog(self, indxname, querystr=""):
        zcat = self._getCatalog()
        if not querystr or not zcat: return []
        query = MatchRegexp(indxname, querystr)
        brains = zcat.evalAdvancedQuery(query)
        return [x.getObject() for x in brains]
        
    def searchLinksByType(self, linktype):
        return self.query_catalog('link_type', linktype)

    def searchLinksByLayer(self, layernum):
        return self.query_catalog('OSI_layer', linktype)
        
    def searchLinksByEndpoint(self, epointname):
        return self.query_catalog('getEndpointNames', epointname)

    def getAdvancedQueryLinkList(self, offset=0, count=50, filter='',
                                 orderby='OSI_layer', orderdir='asc'):
        zcat = self._getCatalog()._catalog
        filter='(?is).*%s.*' % filter
        filterquery = Or(
            MatchRegexp('OSI_layer', filter),
            MatchRegexp('getEndpointNames', filter),
            MatchRegexp('link_type', filter)
        )
        objects = zcat.evalAdvancedQuery(filterquery, ((orderby, orderdir),))
        objects = list(objects)
        totalCount = len(objects)
        offset, count = int(offset), int(count)
        return totalCount, objects[offset:offset+count]

    def getJSONLinkInfo(self, offset=0, count=50, filter='',
                        orderby='OSI_layer', orderdir='asc'):
        """ Returns a batch of links in JSON format """
        totalCount, linkList = self.getAdvancedQueryLinkList(
            offset, count, filter, orderby, orderdir)
        results = [x.getObject().getDataForJSON() + ['odd']
                   for x in linkList]
        return simplejson.dumps((results, totalCount))

    def getChildLinks(self, context):
        """ Returns all links under a given Organizer, aggregated """
        from sets import Set
        result = Set([])
        severities = {}
        siblings = context.children()
        for sibling in siblings:
            links = sibling.getLinks()
            for x in links:
                severities[x.getGeomapData(sibling)] = max(
                    x.getStatus(),
                    severities.get(x.getGeomapData(sibling), 0)
                ) 
            result.update([x.getGeomapData(sibling) for x in links])
        addresses = [x for x in list(result) if x]
        severities = [severities[x] for x in addresses]
        return map(list, zip(map(list, addresses), severities))


InitializeClass(LinkManager)
