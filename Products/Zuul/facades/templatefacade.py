###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import logging
from itertools import imap
from zope.component import adapts
from zope.interface import implements
from Products.Zuul.interfaces import ICatalogTool
from Products.Zuul.interfaces import ITemplateNode
from Products.Zuul.interfaces import ITemplateLeaf
from Products.Zuul.utils import unbrain
from Products.Zuul.facades import ZuulFacade
from Products.ZenModel.RRDTemplate import RRDTemplate

log = logging.getLogger('zen.TemplateFacade')

DATA_SOURCES_EXAMPLE_DATA = [
    {
        'name': 'iaLoadInt5',
        'source': '1.3.6.1.4.1.2021.10.1.5.2',
        'enabled': True,
        'type': 'SNMP'
    }, {
        'name': 'memAvailReal',
        'source': '1.3.6.1.4.1.2021.4.6.0',
        'enabled': True,
        'type': 'Guage'
    }, {
        'name': 'memAvailSwap',
        'source': '1.3.6.1.4.1.2021.4.4.0',
        'enabled': True,
        'type': 'SNMP'
    }, {
        'name': 'memBuffer',
        'source': '1.3.6.1.4.1.2021.4.14.0',
        'enabled': True,
        'type': 'Guage',
        'expanded': True,
        'children':[{
            'name': 'poll_check',
            'source': '/usr/bin/snmpget -Ov -Oq',
            'enabled': True,
            'type': 'COMMAND',
            'leaf': True
        }]
    }, {
        'name': 'memCached',
        'source': '1.3.6.1.4.1.2021.4.15.0',
        'enabled': True,
        'type': 'SNMP'
    }, {
        'name': 'SSCpuRawIdle',
        'source': '1.3.6.1.5.1.2021.11.53.0',
        'enabled': True,
        'type': 'SNMP'
    }, {
        'name': 'SSCpuRawSystem',
        'source': '1.3.6.1.5.1.2021.10.11.52.0',
        'enabled': True,
        'type': 'Guage'
    }, {
        'name': 'SSCpuRawUser',
        'source': '1.3.6.1.5.1.2021.10.11.50.0',
        'enabled': False,
        'type': 'SNMP'
    }, {
        'name': 'SSCpuRawWait',
        'source': '1.3.6.1.5.1.2021.10.11.55.0',
        'enabled': True,
        'type': 'Guage'
    }, {
        'name': 'sysUpTime',
        'source': '1.3.6.1.5.1.2021.1.0.0',
        'enabled': True,
        'type': 'SNMP'
    }
]

class TemplateFacade(ZuulFacade):

    def getTemplates(self, uid):
        deviceClass = self._dmd.unrestrictedTraverse(uid)
        catalog = ICatalogTool(deviceClass)
        brains = catalog.search(types=RRDTemplate)
        nodes = {}
        for template in imap(unbrain, brains):
            if template.id not in nodes:
                nodes[template.id] = ITemplateNode(template)
            leaf = ITemplateLeaf(template)
            nodes[template.id]._addChild(leaf)
        templates = []
        for key in sorted(nodes.keys(), key=str.lower):
            templates.append(nodes[key])
        return templates

    def getDataSources(self, uid):
        return DATA_SOURCES_EXAMPLE_DATA
