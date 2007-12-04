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

import types
import time

import logging
log = logging.getLogger("zen.RRDView")

from Acquisition import aq_chain

from Products.ZenUtils import Map

from Products.ZenModel.ConfigurationError import ConfigurationError

CACHE_TIME = 60.

_cache = Map.Locked(Map.Timed({}, CACHE_TIME))

def GetRRDPath(deviceOrComponent):
    d = deviceOrComponent.device()
    if not d:
        return "Devices/" + deviceOrComponent.id
    skip = len(d.getPrimaryPath()) - 1
    return 'Devices/' + '/'.join(deviceOrComponent.getPrimaryPath()[skip:])


class RRDViewError(Exception): pass


class RRDView(object):
    """
    Mixin to provide hooks to RRD management functions
    """

    def getGraphDefUrl(self, graph, drange=None, template=None):
        """resolve template and graph names to objects 
        and pass to graph performance"""
        if not drange: drange = self.defaultDateRange
        templates = self.getRRDTemplates()
        if template:
            templates = [template]
        if type(graph) in types.StringTypes:
            for t in templates:
                if hasattr(t.graphDefs, graph):
                    template = t
                    graph = getattr(t.graphDefs, graph)
                    break
        targetpath = self.rrdPath()
        objpaq = self.primaryAq()
        perfServer = objpaq.device().getPerformanceServer()
        if perfServer:
            return perfServer.performanceGraphUrl(objpaq, targetpath, 
                                                  template, graph, drange)

    def cacheRRDValue(self, dsname, default = "Unknown"):
        "read an RRDValue with and cache it"
        filename = self.getRRDFileName(dsname)
        value = None
        try:
            value = _cache[filename]
            if value is None:
                return default
        except KeyError:
            pass
        try:
            value = self.getRRDValue(dsname)
        except Exception:
            log.error('Unable to cache value for %s', dsname)
        _cache[filename] = value
        if value is None:
            return default
        return value


    def getRRDValue(self, dsname, start=None, end=None, function="LAST"):
        """Return a single rrd value from its file using function.
        """
        dsnames = (dsname,)
        results = self.getRRDValues(dsnames, start, end, function)
        if results:
            return results[dsname]


    def getRRDDataPoints(self):
        result = []
        for t in self.getRRDTemplates():
            result += t.getRRDDataPoints()
        return result
        
        
    def getRRDDataPoint(self, dpName):
        result = None
        for t in self.getRRDTemplates():
            for dp in t.getRRDDataPoints():
                if dp.name() == dpName:
                    result = dp
                    break
        return result
        
        
    def getRRDValues(self, dsnames, start=None, end=None, function="LAST"):
        """Return a dict of key value pairs where dsnames are the keys.
        """
        try:
            if not start:
                start = time.time() - self.defaultDateRange
            gopts = []
            names = list(dsnames[:])
            for dsname in dsnames:
                for dp in self.getRRDDataPoints():
                    if dp.name().find(dsname) > -1:
                        break
                else:
                    names.remove(dsname)
                    continue
                filename = self.getRRDFileName(dp.name())
                rpn = str(dp.rpn)
                if rpn:
                    rpn = "," + rpn
                gopts.append("DEF:%s_r=%s:ds0:AVERAGE" % (dsname,filename))
                gopts.append("CDEF:%s_c=%s_r%s" % (dsname,dsname,rpn))
                gopts.append("VDEF:%s=%s_c,%s" % (dsname,dsname,function))
                gopts.append("PRINT:%s:%%.2lf" % (dsname))
                gopts.append("--start=%d" % start)
                if end:
                    gopts.append("--end=%d" % end)
            perfServer = self.device().getPerformanceServer()
            vals = []
            if perfServer:
                vals = perfServer.performanceCustomSummary(gopts)
                if vals is None:
                    vals = [None] * len(gopts)
            def cvt(val):
                if val is None: return val
                val = float(val)
                if val != val: return None
                return val
            return dict(zip(names, map(cvt, vals)))
        except Exception, ex:
            log.exception(ex)
        
        
    
    def getRRDSum(self, points, start=None, end=None, function="LAST"):
        "Return a some of listed datapoints."
        
        try:
            if not start:
                start = time.time() - self.defaultDateRange
            if not end:
                end = time.time()
            gopts = []
            for name in points:
                for dp in self.getRRDDataPoints():
                    if dp.name().find(name) > -1:
                        break
                else:
                    raise RRDViewError("Unable to find data point %s" % name)
                filename = self.getRRDFileName(dp.name())
                rpn = str(dp.rpn)
                if rpn:
                    rpn = "," + rpn
                gopts.append("DEF:%s_r=%s:ds0:AVERAGE" % (name, filename))
                gopts.append("CDEF:%s=%s_r%s" % (name, name, rpn))
            gopts.append("CDEF:sum=%s%s" % (','.join(points),
                                             ',+'*(len(points)-1)))
            gopts.append("VDEF:agg=sum,%s" % function)
            gopts.append("PRINT:agg:%.2lf")
            gopts.append("--start=%d" % start)
            gopts.append("--end=%d" % end)
            perfServer = self.device().getPerformanceServer()
            if perfServer:
                vals = perfServer.performanceCustomSummary(gopts)
                if vals is None:
                    return None
                return float(vals[0])
        except Exception, ex:
            log.exception(ex)
        
    
    def getDefaultGraphDefs(self, drange=None):
        """get the default graph list for this object"""
        graphs = []
        for template in self.getRRDTemplates():
            for g in template.getGraphDefs():
                graph = {}
                graph['title'] = g.getId()
                try:
                    graph['url'] = self.getGraphDefUrl(g, drange, template)
                    graphs.append(graph)
                except ConfigurationError:
                    pass
        return graphs
        
        
    def getGraphDef(self, graphId):
        ''' Fetch a graph by id.  if not found return None
        '''
        for t in self.getRRDTemplates():
            for g in t.getGraphDefs():
                if g.id == graphId:
                    return g
        return None
            
    
    def getRRDTemplateName(self):
        """Return the target type name of this component.  By default meta_type.
        Override to create custom type selection.
        """
        return self.meta_type


    def getRRDFileName(self, dsname):
        """Look up an rrd file based on its data point name"""
        names = [p.name() for p in self.getRRDDataPoints()
                 if p.name().endswith(dsname)]
        if names:
            return '%s/%s.rrd' % (self.rrdPath(), names[0])
        else:
            return '%s/%s.rrd' % (self.rrdPath(), dsname)


    def getRRDNames(self):
        return []

    def getRRDPaths(self):
        return map(self.getRRDFileName, self.getRRDNames())

    def snmpIgnore(self):
        """Should this component be monitored for performance using snmp.
        """
        return False

    def getRRDTemplates(self):
        default = self.getRRDTemplateByName(self.getRRDTemplateName())
        if not default:
            return []
        return [default]

    def getRRDTemplate(self):
        try:
            return self.getRRDTemplates()[0]
        except IndexError:
            return None

    def getRRDTemplateByName(self, name):
        "Return the template of the given name."
        try:
            return self._getOb(name)
        except AttributeError:
            pass
        for obj in aq_chain(self):
            try:
                return obj.rrdTemplates._getOb(name)
            except AttributeError:
                pass
        return None


    def getThresholds(self, templ):
        """Return a dictionary where keys are dsnames and values are thresholds.
        """
        result = {}
        for thresh in templ.thresholds():
            if not thresh.enabled: continue
            for dsname in thresh.dsnames:
                threshdef = result.setdefault(dsname, [])
                threshdef.append(thresh.getConfig(self))
        return result


    def rrdPath(self):
        return GetRRDPath(self)


    def fullRRDPath(self):
        from PerformanceConf import performancePath
        return performancePath(self.rrdPath())
        
    def getSnmpOidTargets(self):
        """Return a list of (name, oid, path, type, createCmd, thresholds)
        that define monitorable"""
        oids = []
        if self.snmpIgnore(): return (oids, [])
        basepath = self.rrdPath()
        perfServer = self.device().getPerformanceServer()
        for templ in self.getRRDTemplates():
            for ds in templ.getRRDDataSources("SNMP"):
                if not ds.enabled: continue
                oid = ds.oid
                snmpindex = getattr(self, "ifindex", self.snmpindex)
                if snmpindex: oid = "%s.%s" % (oid, snmpindex)
                for dp in ds.getRRDDataPoints():
                    cname = self.meta_type != "Device" \
                                and self.viewName() or dp.id
                    oids.append((cname,
                                 oid,
                                 "/".join((basepath, dp.name())),
                                 dp.rrdtype,
                                 dp.getRRDCreateCommand(perfServer),
                                 (dp.rrdmin, dp.rrdmax)))
        return (oids, self.getThresholdInstances('SNMP'))


    def getDataSourceCommands(self):
        """Return list of command definitions.
        """
        result = []
        perfServer = self.device().getPerformanceServer()
        for templ in self.getRRDTemplates():
            basepath = self.rrdPath()
            for ds in templ.getRRDDataSources('COMMAND'):
                if not ds.enabled: continue
                points = []
                for dp in ds.getRRDDataPoints():
                    points.append(
                        (dp.id,
                         "/".join((basepath, dp.name())),
                         dp.rrdtype,
                         dp.getRRDCreateCommand(perfServer),
                         (dp.rrdmin, dp.rrdmax)))
                key = ds.eventKey or ds.id
                result.append( (getattr(ds, 'usessh', False), 
                                ds.cycletime, ds.component,
                                ds.eventClass, key, ds.severity,
                                ds.getCommand(self), points) )
        return (result, self.getThresholdInstances('COMMAND'))


    def getThresholdInstances(self, dsType):
        result = []
        for template in self.getRRDTemplates():
            # if the template refers to a data source name of the right type
            # include it
            names = []
            for ds in template.getRRDDataSources(dsType):
                for dp in ds.datapoints():
                    names.append(dp.name())
            for threshold in template.thresholds():
                if not threshold.enabled: continue
                for ds in threshold.dsnames:
                    if ds in names:
                        result.append(threshold.createThresholdInstance(self))
                        break
        return result

    def makeLocalRRDTemplate(self, templateName=None, REQUEST=None):
        """Make a local copy of our RRDTemplate if one doesn't exist.
        """
        if templateName is None: templateName = self.getRRDTemplateName()
        if not self.isLocalName(templateName):
            ct = self.getRRDTemplateByName(templateName)._getCopy(self)
            ct.id = templateName
            self._setObject(ct.id, ct)
        if REQUEST: 
            REQUEST['message'] = 'Local copy %s created' % templateName
            return self.callZenScreen(REQUEST)


    def removeLocalRRDTemplate(self, templateName=None, REQUEST=None):
        """Make a local delete of our RRDTemplate if one doesn't exist.
        """
        if templateName is None: templateName = self.getRRDTemplateName()
        if self.isLocalName(templateName):
            self._delObject(templateName)
        if REQUEST: 
            REQUEST['message'] = 'Local copy %s removed' % templateName
            return self.callZenScreen(REQUEST)


def updateCache(filenameValues):
    _cache.update(dict(filenameValues))
