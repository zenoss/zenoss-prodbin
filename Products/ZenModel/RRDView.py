##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import time

from xmlrpclib import ProtocolError
import logging
log = logging.getLogger("zen.RRDView")

from Acquisition import aq_chain

from Products.ZenRRD.RRDUtil import convertToRRDTime
from Products.ZenUtils import Map
from Products.ZenWidgets import messaging

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
        if isinstance(graph, basestring):
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
        """
        Cache RRD values for up to CACHE_TIME seconds.
        """
        # Notes:
        #  * _cache takes care of the time-limited-offer bits
        #  * rrdcached does cache results, but the first query
        #    could potentially cause a flush()
        #  * Remote collectors need this call to prevent extra
        #    calls across the network
        filename = self.getRRDFileName(dsname)
        try:
            value = _cache[filename]
        except KeyError:
            try:
                # Grab rrdcached value locally or from network
                value = self.getRRDValue(dsname)
            except Exception, ex:
                # Generally a remote collector issue
                # We'll cache this for a minute and then try again
                value = None
                log.error('Unable to get RRD value for %s: %s', dsname, ex)
            _cache[filename] = value
        
        return value if value is not None else default


    def getRRDValue(self, dsname, start=None, end=None, function="LAST",
                    format="%.2lf", extraRpn="", cf="AVERAGE"):
        """Return a single rrd value from its file using function.
        """
        dsnames = (dsname,)
        results = self.getRRDValues(
            dsnames, start, end, function, format, extraRpn, cf=cf)
        if results and dsname in results:
            return results[dsname]

    def _getRRDDataPointsGen(self):
        for t in self.getRRDTemplates():
            for dp in t.getRRDDataPoints():
                yield dp

    def getRRDDataPoints(self):
        return list(self._getRRDDataPointsGen())

    def getRRDDataPoint(self, dpName):
        return next((dp for dp in self._getRRDDataPointsGen() 
                                    if dp.name() == dpName), None)

    def fetchRRDValues(self, dpnames, cf, resolution, start, end=""):
        paths = [self.getRRDFileName(dpname) for dpname in dpnames]
        return self.device().getPerformanceServer().fetchValues(paths,
            cf, resolution, start, end)


    def fetchRRDValue(self, dpname, cf, resolution, start, end=""):
        r = self.fetchRRDValues([dpname,], cf, resolution, start, end=end)
        if r:
            return r[0]
        return None


    def getRRDValues(self, dsnames, start=None, end=None, function="LAST",
                     format="%.2lf", extraRpn="", cf="AVERAGE"):
        """
        Return a dict of key value pairs where dsnames are the keys.
        """
        try:
            if not start:
                start = time.time() - self.defaultDateRange
            gopts = []
            # must copy dsnames into mutable list
            names = list(dsnames)
            for dsname in dsnames:
                dp = next((d for d in self._getRRDDataPointsGen() 
                                        if dsname in d.name()), None)
                if dp is None:
                    names.remove(dsname)
                    continue
                filename = self.getRRDFileName(dp.name())
                rpn = str(dp.rpn)
                if rpn:
                    rpn = "," + rpn
                if extraRpn:
                    rpn = rpn + "," + extraRpn

                gopts.append("DEF:%s_r=%s:ds0:%s" % (dsname,filename,cf))
                gopts.append("CDEF:%s_c=%s_r%s" % (dsname,dsname,rpn))
                gopts.append("VDEF:%s=%s_c,%s" % (dsname,dsname,function))
                gopts.append("PRINT:%s:%s" % (dsname, format))
                gopts.append("--start=%s" % convertToRRDTime(start))
                if end:
                    gopts.append("--end=%s" % convertToRRDTime(end))
            if not names:
                return {}
            perfServer = self.device().getPerformanceServer()
            vals = []
            if perfServer:
                vals = perfServer.performanceCustomSummary(gopts)
                if vals is None:
                    vals = [None] * len(dsnames)
            def cvt(val):
                if val is None or val.lower() == "nan":
                    return None
                return float(val)
            return dict(zip(names, map(cvt, vals)))
        except ProtocolError as e:
            log.warn("Unable to get RRD values for %s: %s for URL %s" % (
                self.getPrimaryId(), e.errmsg, e.url))
        except Exception, ex:
            log.exception("Unable to collect RRD Values for %s" % self.getPrimaryId())



    def getRRDSum(self, points, start=None, end=None, function="LAST"):
        "Return a some of listed datapoints."

        try:
            if not start:
                start = time.time() - self.defaultDateRange
            if not end:
                end = time.time()
            gopts = []
            for name in points:
                dp = next((dp_ for dp_ in self._getRRDDataPointsGen() 
                                    if name in dp_.name()), None)
                if dp is None:
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
        return next((g for t in self.getRRDTemplates() 
                                for g in t.getGraphDefs() 
                                    if g.id == graphId), 
                         None)

    def getRRDTemplateName(self):
        """Return the target type name of this component.  By default meta_type.
        Override to create custom type selection.
        """
        return self.meta_type


    def getRRDFileName(self, dsname):
        """Look up an rrd file based on its data point name"""
        nm = next((p.name() for p in self._getRRDDataPointsGen() 
                            if p.name().endswith(dsname)), dsname)
        return '%s/%s.rrd' % (self.rrdPath(), nm)


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

    def getRRDContextData(self, context):
        return context

    def getThresholdInstances(self, dsType):
        from Products.ZenEvents.Exceptions import pythonThresholdException
        result = []
        for template in self.getRRDTemplates():
            # if the template refers to a data source name of the right type
            # include it
            names = set(dp.name() for ds in template.getRRDDataSources(dsType) 
                                for dp in ds.datapoints())
            for threshold in template.thresholds():
                if not threshold.enabled: continue
                for ds in threshold.dsnames:
                    if ds in names:
                        try:
                            thresh = threshold.createThresholdInstance(self)
                            result.append(thresh)
                        except pythonThresholdException, ex:
                            log.warn(ex)
                            zem = self.primaryAq().getEventManager()
                            import socket
                            device = socket.gethostname()
                            path = template.absolute_url_path()
                            msg = \
"The threshold %s in template %s has caused an exception." % (threshold.id, path)
                            evt = dict(summary=str(ex), severity=3,
                                    component='zenhub', message=msg,
                                    dedupid='zenhub|' + str(ex),
                                    template=path,
                                    threshold=threshold.id,
                                    device=device, eventClass="/Status/Update",)
                            zem.sendEvent(evt)
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
            messaging.IMessageSender(self).sendToBrowser(
                'Template Created',
                'Local copy "%s" created.' % templateName
            )
            return self.callZenScreen(REQUEST)


    def removeLocalRRDTemplate(self, templateName=None, REQUEST=None):
        """Make a local delete of our RRDTemplate if one doesn't exist.
        """
        if templateName is None: templateName = self.getRRDTemplateName()
        if self.isLocalName(templateName):
            self._delObject(templateName)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Template Removed',
                'Local copy "%s" removed.' % templateName
            )
            return self.callZenScreen(REQUEST)


def updateCache(filenameValues):
    _cache.update(dict(filenameValues))
