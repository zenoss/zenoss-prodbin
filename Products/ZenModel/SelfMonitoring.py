###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from base64 import urlsafe_b64encode
from urllib import urlencode
import zlib

from Products.ZenModel.RRDView import RRDView
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenModel.TemplateContainer import TemplateContainer
from Products.ZenUtils.Utils import zenPath

from AccessControl import ClassSecurityInfo, Permissions

def performancePath(target):
    """
    Return the base directory where RRD performance files are kept.

    @param target: path to performance file
    @type target: string
    @return: sanitized path to performance file
    @rtype: string
    """
    if target.startswith('/'):
        target = target[1:]
    return zenPath('perf', target)


class SelfMonitoring(ZenModelRM, RRDView, TemplateContainer):
    """
    SelfPerformance provides a UI interface for self monitoring statistics that
    are independent of collectors or hubs.
    """
    
    meta_type = "SelfMonitoring"
    
    # Meta-Data: Zope access control
    security = ClassSecurityInfo()

    def getRRDTemplates(self, *args, **kwargs):
        return [self.zenossTemplate,]

    def rrdPath(self):
        return 'Daemons/localhost/'

    def getRRDContextData(self, context):
        context['here'] = self
        context['name'] = self.id
        return context

    def getGraphDefUrl(self, graph, drange=None, template=None):
        """resolve template and graph names to objects
        and pass to graph performance"""
        if not drange: drange = self.defaultDateRange
        templates = self.getRRDTemplates()
        if template:
            templates = [template]
        if isinstance(graph, basestring):
            for t in templates:
                if hasattr(t.graphDefs, graph):
                    template = t
                    graph = getattr(t.graphDefs, graph)
                    break
        targetpath = self.rrdPath()
        objpaq = self.primaryAq()
        return self.performanceGraphUrl(objpaq, targetpath, template, graph, drange)

    def performanceGraphUrl(self, context, targetpath, targettype, view, drange):
        """
        Set the full path of the target and send to view

        @param context: Where you are in the Zope acquisition path
        @type context: Zope context object
        @param targetpath: device path of performance metric
        @type targetpath: string
        @param targettype: unused
        @type targettype: string
        @param view: view object
        @type view: Zope object
        @param drange: date range
        @type drange: string
        @return: URL to graph
        @rtype: string
        """
        targetpath = performancePath(targetpath)
        gopts = view.getGraphCmds(context, targetpath)
        return self.buildGraphUrlFromCommands(gopts, drange)

    def buildGraphUrlFromCommands(self, gopts, drange):
        """
        Return an URL for the given graph options and date range

        @param gopts: graph options
        @type gopts: string
        @param drange: time range to use
        @type drange: string
        @return: URL to a graphic
        @rtype: string
        """
        newOpts = []
        width = 0
        for o in gopts:
            if o.startswith('--width'):
                width = o.split('=')[1].strip()
                continue
            newOpts.append(o)

        encodedOpts = urlsafe_b64encode(
            zlib.compress('|'.join(newOpts), 9))
        params = {
            'gopts': encodedOpts,
            'drange': drange,
            'width': width,
        }
        params = urlencode(params)

        return '/zport/RenderServer/render?%s' % (params,)

