#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

import os
import types
import time
import glob

import logging
log = logging.getLogger("zen.RRDView")

from Acquisition import aq_base, aq_chain

from Products.ZenRRD.Exceptions import RRDObjectNotFound
from Products.ZenUtils import Map

from Products.ZenUtils.ZenTales import talesEval
from Products.ZenModel.ConfigurationError import ConfigurationError

CACHE_TIME = 60.

_cache = Map.Locked(Map.Timed({}, CACHE_TIME))

class RRDViewError(Exception): pass


class RRDView(object):
    """
    Mixin to provide hooks to RRD management functions
    """

    def getRRDGraphUrl(self, graph, drange=None, template=None):
        """resolve template and graph names to objects 
        and pass to graph performance"""
        if not drange: drange = self.defaultDateRange
        templates = self.getRRDTemplates()
        if template:
            templates = [template]
        if type(graph) in types.StringTypes:
            def getGraph(templates, graphName):
                for t in templates:
                    try:
                        return t, t._getOb(graphName)
                    except AttributeError:
                        pass
            template, graph = getGraph(templates, graph)
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
        
        
    def getRRDValues(self, dsnames, start=None, end=None, function="LAST"):
        """Return a dict of key value pairs where dsnames are the keys.
        """
        try:
            if not start:
                start = time.time() - self.defaultDateRange
            res = {}.fromkeys(dsnames, None)
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
            names = list(points[:])
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
        
    
    def getDefaultGraphs(self, drange=None):
        """get the default graph list for this object"""
        graphs = []
        for template in self.getRRDTemplates():
            for g in template.getGraphs():
                graph = {}
                graph['title'] = g.getId()
                try:
                    graph['url'] = self.getRRDGraphUrl(g, drange, template)
                    graphs.append(graph)
                except ConfigurationError:
                    pass
        return graphs
            
    
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
        d = self.device()
        if not d: return "/Devices/" + self.id
        skip = len(d.getPrimaryPath()) - 1
        return '/Devices/' + '/'.join(self.getPrimaryPath()[skip:])
        
    def getSnmpOidTargets(self):
        """Return a list of (name, oid, path, type, createCmd, thresholds)
        that define monitorable"""
        oids = []
        if self.snmpIgnore(): return oids 
        basepath = self.rrdPath()
        for templ in self.getRRDTemplates():
            threshs = self.getThresholds(templ)
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
                                 dp.createCmd,
                                 (dp.rrdmin, dp.rrdmax),
                                 threshs.get(dp.name(),[])))
        return oids


    def getDataSourceCommands(self):
        """Return list of command definitions.
        """
        result = []
        for templ in self.getRRDTemplates():
            threshs = self.getThresholds(templ)
            basepath = self.rrdPath()
            dataSources = templ.getRRDDataSources('COMMAND')
            for ds in dataSources:
                if not ds.enabled: continue
                points = []
                for dp in ds.getRRDDataPoints():
                    points.append(
                        (dp.id,
                         "/".join((basepath, dp.name())),
                         dp.rrdtype,
                         dp.createCmd,
                         (dp.rrdmin, dp.rrdmax),
                         threshs.get(dp.name(),[])))
                key = ds.eventKey or ds.id
                result.append( (ds.usessh, ds.cycletime, ds.component,
                                ds.eventClass, key, ds.severity,
                                ds.getCommand(self), points) )
        return result


    def getXmlRpcTargets(self):
        """Return a list of XMLRPC targets in the form
        [(name, url, methodName, methodParameters, path, type, 
        createCmd, thresholds),...]
        """
        targets = []
        '''TODO this should probably be xmlrpcIgnore()'''
        '''Either snmpIgnore always returns false or it gets overridden
        and returns true if the device is operationally down. It is not
        clear what needs to be done here for the xmlrpc code.'''
        if self.snmpIgnore(): return targets
        basepath = self.rrdPath()
        try:
            for templ in self.getRRDTemplates():
                threshs = self.getThresholds(templ)
                for ds in templ.getRRDDataSources("XMLRPC"):
                    if not ds.enabled: continue
                    url = talesEval('string:' + ds.xmlrpcURL, self.device())
                    username = ds.xmlrpcUsername
                    password = ds.xmlrpcPassword
                    methodName = ds.xmlrpcMethodName
                    methodParameters = ds.xmlrpcMethodParameters
                    cname = self.meta_type != "Device" \
                                and self.viewName() or ds.id
                    points = []
                    for dp in ds.getRRDDataPoints():
                        points.append(
                            (dp.id,
                             "/".join((basepath, dp.name())),
                             dp.rrdtype,
                             dp.createCmd,
                             (dp.rrdmin, dp.rrdmax),
                             threshs.get(dp.name(),[])))
                    targets.append((cname,
                                    url,
                                    (username, password),
                                    methodName,
                                    methodParameters,
                                    points))
        except RRDObjectNotFound, e:
            log.warn(e)
        return targets


    def copyRRDTemplate(self, REQUEST=None):
        """Make a local copy of our RRDTemplate if one doesn't exist.
        """
        templname = self.getRRDTemplateName()
        if not self.isLocalName(templname):
            ct = self.getRRDTemplate()._getCopy(self)
            ct.id = self.getRRDTemplateName()
            self._setObject(ct.id, ct)
        if REQUEST: return self.callZenScreen(REQUEST)


    def deleteRRDTemplate(self, REQUEST=None):
        """Make a local delete of our RRDTemplate if one doesn't exist.
        """
        tname = self.getRRDTemplateName()
        if self.isLocalName(tname):
            self._delObject(tname)
        if REQUEST: return self.callZenScreen(REQUEST)


def updateCache(filenameValues):
    _cache.update(dict(filenameValues))
