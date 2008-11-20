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

from Products.Five.browser import BrowserView
from Products.ZenUtils.json import json

class DeviceComponentTable(BrowserView):
    """
    Populates the component table that appears on the device status page.
    """
    def __call__(self):
        return self.getDeviceComponentEventSummary(self.context)

    @json
    def getDeviceComponentEventSummary(self, device):
        """
        Return a list of categories of components on a device along with event
        pills for the maximum severity event on each category in the form of a
        JSON object ready for inclusion in a YUI data table. If a category
        contains components with events, the component and its associated event
        pill are returned as a separate (indented) row.

        @param device: The device for which to gather component data
        @type device: L{Device}
        @return: A dictionary representation of the columns and rows of the
        table
        @rtype: dict
        """
        zem = self.context.ZenEventManager
        mydict = {'columns':[], 'data':[]}
        mydict['columns'] = ['Component Type', 'Status']
        devdata = []
        query = { 'getParentDeviceName':device.id,}
        brains = device.componentSearch(query)
        metatypes = set([str(x.meta_type) for x in brains])
        resultdict = {}
        for mt in metatypes: resultdict[mt] = {}
        evpilltemplate = ('<img src="img/%s_dot.png" '
                          'width="15" height="15" '
                          'style="cursor:hand;cursor:pointer" '
                          'onclick="location.href'
                          '=\'%s/viewEvents\'"/>')
        linktemplate = ("<a href='%s' class='prettylink'>"
                        "<div class='device-icon-container'>%s "
                        "</div>%s</a>")
        colors = "green grey blue yellow orange red".split()
        indent = "&nbsp;"*8
        def getcompfrombrains(id):
            for comp in brains:
                compid = comp.getPrimaryId.split('/')[-1]
                if compid==id: 
                    return comp.getPrimaryId, comp.meta_type, comp.getPath()
            return None, None, None
        devurl = device.getPrimaryUrlPath()
        ostab = devurl.rstrip('/') + '/os'
        for event in zem.getEventListME(device):
            if not len(event.component): continue
            id, metatype, url = getcompfrombrains(event.component)
            if id is None or metatype is None or url is None: 
                id, metatype, url = event.component, 'Other', devurl + '/os'
            tally = resultdict.setdefault(metatype, 
                            {'sev':event.severity, 
                             'components': {id: (event.severity, 1, id, ostab)}})
            tally.setdefault('sev', event.severity)
            tally.setdefault('components', {id: (event.severity, 0, id, ostab)})
            if tally['sev'] < event.severity: tally['sev'] = event.severity
            comp = tally['components'].setdefault(id, (event.severity, 0, 
                                                       id, ostab))
            comptotal = tally['components'][id][1]
            compsev = tally['components'][id][0]
            newsev = compsev
            if event.severity > compsev: newsev = event.severity
            tally['components'][id] = (newsev, comptotal+1, id, url)
        r = resultdict
        categorysort = [(r[x]['sev'], len(r[x]['components']), x,
                         r[x]['components'].values()) for x in r if r[x]]
        categorysort.sort(); categorysort.reverse()
        categorysort.extend([(0, 0, x, []) for x in r if not r[x]])
        for bunch in categorysort:
            catsev, catnum, catname, comps = bunch
            catlink = ostab
            catcolor = colors[catsev]
            evpill = evpilltemplate % (catcolor, device.getPrimaryUrlPath())
            if catnum: evpill = ''
            devdata.append((linktemplate % (catlink, '', catname), evpill))
            comps.sort()
            for comp in comps:
                compsev, compnum, complink, compurl = comp
                compcolor = colors[compsev]
                if not complink.startswith('/zport'): 
                    compname = complink
                    complink = devurl.rstrip('/') + '/viewEvents'
                else: 
                    compname = complink.split('/')[-1]
                    complink = compurl.rstrip('/') + '/viewEvents'
                if not compname: continue
                compname = "<strong>%s</strong>" % compname
                devdata.append(
                    (linktemplate % (complink, '', indent+compname),
                     evpilltemplate % (compcolor, 
                                       device.getPrimaryUrlPath())
                    )
                )
        mydict['data'] = [{'Component Type':x[0],
                           'Status':x[1]} for x in devdata]
        return mydict
