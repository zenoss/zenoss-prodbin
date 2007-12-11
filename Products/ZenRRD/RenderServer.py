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

__doc__="""RenderServer

Frontend that passes rrd graph options to rrdtool to render.  

$Id: RenderServer.py,v 1.14 2003/06/04 18:25:58 edahl Exp $"""

__version__ = "$Revision: 1.14 $"[11:-2]

import os
import time
import logging
import urllib
import zlib
import mimetypes

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from Globals import DTMLFile

try:
    import rrdtool
except ImportError:
    pass

try:
    from base64 import urlsafe_b64decode
    raise ImportError
except ImportError:
    def urlsafe_b64decode(s):
        import base64
        return base64.decodestring(s.replace('-','+').replace('_','/'))

from Products.ZenUtils.PObjectCache import PObjectCache
from Products.ZenUtils.Utils import zenPath

from RRDToolItem import RRDToolItem

from Products.ZenModel.PerformanceConf import performancePath
import glob
import tarfile

log = logging.getLogger("RenderServer")


def manage_addRenderServer(context, id, REQUEST = None):
    """make a RenderServer"""
    rs = RenderServer(id)
    context._setObject(id, rs)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
                                     

addRenderServer = DTMLFile('dtml/addRenderServer',globals())


class RenderServer(RRDToolItem):

    meta_type = "RenderServer"

    cacheName = 'RRDRenderCache'
    
    security = ClassSecurityInfo()

    def __init__(self, id, tmpdir = '/tmp/renderserver', cachetimeout=300):
        self.id = id
        self.tmpdir = tmpdir
        self.cachetimeout = cachetimeout

    security.declareProtected('View', 'render')
    def render(self, gopts=None, start=None, end=None, drange=None, 
               remoteUrl=None, width=None, ftype='PNG', getImage=True, 
               graphid='', comment=None, REQUEST=None):
        """render a graph and return it"""
        gopts = zlib.decompress(urlsafe_b64decode(gopts))
        gopts = gopts.split('|')
        gopts.append('--width=%s' % width)
        if start:
            gopts.append('--start=%s' % start)
        if end:
            gopts.append('--end=%s' % end)
        drange = int(drange)
        id = self.graphId(gopts, drange, ftype)
        graph = self.getGraph(id, ftype, REQUEST)
        if not graph:
            if not os.path.exists(self.tmpdir):
                os.makedirs(self.tmpdir, 0750)
            filename = "%s/graph-%s" % (self.tmpdir,id)
            if remoteUrl:
                f = open(filename, "w")
                f.write(urllib.urlopen(remoteUrl).read())
                f.close()
            else:            
                if ftype.lower()=='html': 
                    imgtype = 'PNG'
                else:
                    imgtype = ftype
                gopts.insert(0, "--imgformat=%s" % imgtype)
                #gopts.insert(0, "--lazy")
                end = int(time.time())-300
                start = end - drange
                gopts.insert(0, 'COMMENT:%s\\c' % comment)
                gopts.insert(0, '--end=%d' % end)
                gopts.insert(0, '--start=%d' % start)
                gopts.insert(0, filename)
                log.error("opts: %r", (gopts,))
                try:
                    rrdtool.graph(*gopts)
                except Exception, ex:    
                    if ex.args[0].find('No such file or directory') > -1:
                        return None
                    log.exception("failed generating graph")
                    log.warn(" ".join(gopts))
                    raise
            self.addGraph(id, filename)
            graph = self.getGraph(id, ftype, REQUEST)
        if getImage: 
            return graph
        else: 
            return """
            <script>
                parent.location.hash = '%s:%s;';
            </script>
            """ % (graphid, str(bool(graph)))

    
    def deleteRRDFiles(self, device, 
                        datasource=None, datapoint=None, 
                        remoteUrl=None, REQUEST=None):
        """
        Delete RRD files associated with the given device id.
        If datapoint is not None then delete the file corresponding to that dp.
        Else if datasource is not None then delete the files corresponding to
          all datapoints in the datasource.
        Else delete all rrd files associated with the given device.
        """
        devDir = performancePath('/Devices/%s' % device)
        if not os.path.isdir(devDir):
            return
        fileNames = []
        dirNames = []
        if datapoint:
            fileNames = [
                performancePath('/Devices/%s/%s.rrd' % (device, datapoint))]
        elif datasource:
            rrdPath = '/Devices/%s/%s_*.rrd' % (device, datasource)
            fileNames = glob.glob(performancePath(rrdPath))
        else:
            for dPath, dNames, dFiles in os.walk(devDir, topdown=False):
                fileNames += [os.path.join(dPath, f) for f in dFiles]
                dirNames += [os.path.join(dPath, d) for d in dNames]
            dirNames.append(devDir)
        for fileName in fileNames:
            try:
                os.remove(fileName)
            except OSError:
                log.warn("File %s does not exist" % fileName)
        for dirName in dirNames:
            try:
                os.rmdir(dirName)
            except OSError:
                log.warn('Directory %s could not be removed' % dirName)
        if remoteUrl:
            urllib.urlopen(remoteUrl)
    
    def packageRRDFiles(self, device, REQUEST=None):
        """Tar a package of RRDFiles"""
        srcdir = performancePath('/Devices/%s' % device)
        tarfilename = '%s/%s.tgz' % (self.tmpdir, device)
        tar = tarfile.open(tarfilename, "w:gz")
        for file in os.listdir(srcdir):
            tar.add('%s/%s' % (srcdir, file), '/%s' % os.path.basename(file))
        tar.close()

    def unpackageRRDFiles(self, device, REQUEST=None):
        """Untar a package of RRDFiles"""
        destdir = performancePath('/Devices/%s' % device)
        tarfilename = '%s/%s.tgz' % (self.tmpdir, device)
        tar = tarfile.open(tarfilename, "r:gz")
        for file in tar.getmembers():
            tar.extract(file, destdir)
        tar.close()

    def receiveRRDFiles(self, REQUEST=None):
        """receive a device's RRD Files from another server"""
        tarfile = REQUEST.get('tarfile')
        tarfilename = REQUEST.get('tarfilename')
        f=open('%s/%s' % (self.tmpdir, tarfilename), 'wb')
        f.write(urllib.unquote(tarfile))
        f.close()
                
    def sendRRDFiles(self, device, server, REQUEST=None):
        """Move a package of RRDFiles"""
        tarfilename = '%s.tgz' % device
        f=open('%s/%s' % (self.tmpdir, tarfilename), 'rb')
        tarfilebody=f.read()
        f.close()
        # urlencode the id, title and file
        params = urllib.urlencode({'tarfilename': tarfilename,
            'tarfile':tarfilebody})
        # send the file to zope
        perfMon = self.dmd.getDmdRoot("Monitors").getPerformanceMonitor(server)
        if perfMon.renderurl.startswith('http'):
            remoteUrl = '%s/receiveRRDFiles' % (perfMon.renderurl)
            urllib.urlopen(remoteUrl, params)
            
    
    def moveRRDFiles(self, device, destServer, srcServer=None, REQUEST=None):
        """send a device's RRD Files to another server"""
        monitors = self.dmd.getDmdRoot("Monitors")
        destPerfMon = monitors.getPerformanceMonitor(destServer)
        if srcServer:
            srcPerfMon = monitors.getPerformanceMonitor(srcServer)
            remoteUrl = '%s/moveRRDFiles?device=%s&destServer=%s' % (srcPerfMon.renderurl, device, destServer)
            urllib.urlopen(remoteUrl)
        else:
            self.packageRRDFiles(device, REQUEST)
            self.sendRRDFiles(device, destServer, REQUEST)
            if destPerfMon.renderurl.startswith('http'):
                remoteUrl = '%s/unpackageRRDFiles?device=%s' % (destPerfMon.renderurl, device)
                urllib.urlopen(remoteUrl)
            else:
                self.unpackageRRDFiles(device, REQUEST)
            
    security.declareProtected('View', 'plugin')
    def plugin(self, name, REQUEST=None):
        "render a custom graph and return it"
        try:
            m = zenPath('Products/ZenRRD/plugins/%s.py' % name)
            graph = None
            exec open(m)
            return graph
        except Exception, ex:
            log.exception("failed generating graph from plugin %s" % name)
            raise


    security.declareProtected('GenSummary', 'summary')
    def summary(self, gopts):
        """return summary information as a list but no graph"""
        gopts.insert(0, '/dev/null') #no graph generated
        try:
            values = rrdtool.graph(*gopts)[2]
        except Exception, ex:
            if ex.args[0].find('No such file or directory') > -1:
                return None
            log.exception("failed generating summary")
            log.warn(" ".join(gopts))
            raise
        return values
        

    security.declareProtected('GenSummary', 'currentValues')
    def currentValues(self, paths):
        """return latest values"""
        try:
            def value(p):
                v = None
                info = None
                try:
                    info = rrdtool.info(p)
                except:
                    log.debug('%s not found' % p)
                if info:
                    last = info['last_update']
                    step = info['step']
                    v = rrdtool.graph('/dev/null',
                                      'DEF:x=%s:ds0:AVERAGE' % p,
                                      'VDEF:v=x,LAST',
                                      'PRINT:v:%.2lf',
                                      '--start=%d'%(last-step),
                                      '--end=%d'%last)
                    v = float(v[2][0])
                    if str(v) == 'nan': v = None
                return v
            return map(value, paths)
        except NameError:
            log.warn("It appears that the rrdtool bindings are not installed properly.")
        except Exception, ex:
            if ex.args[0].find('No such file or directory') > -1:
                return None
            log.exception("failed generating summary")
            raise
        

    def rrdcmd(self, gopts, ftype='PNG'):
        filename, gopts = self._setfile(gopts, ftype)
        return "rrdtool graph " + " ".join(gopts)


    def graphId(self, gopts, drange, ftype):
        import md5
        id = md5.new(''.join(gopts)).hexdigest() 
        id += str(drange) + '.' + ftype.lower()
        return id
    
    def _loadfile(self, filename):
        try:
            f = open(filename)
            graph = f.read()
            f.close()
            return graph
        except IOError:
            log.info("File: %s not created yet." % filename);
            return None


    def setupCache(self):
        """make new cache if we need one"""
        if not hasattr(self, '_v_cache') or not self._v_cache:
            tmpfolder = self.getPhysicalRoot().temp_folder
            if not hasattr(tmpfolder, self.cacheName):
                cache = PObjectCache(self.cacheName, self.cachetimeout)
                tmpfolder._setObject(self.cacheName, cache)
            self._v_cache = tmpfolder._getOb(self.cacheName)
        return self._v_cache


    def addGraph(self, id, filename):
        """add graph to temporary folder"""
        cache = self.setupCache()
        graph = self._loadfile(filename)
        if graph: 
            cache.addToCache(id, graph)
            try: 
                os.remove(filename)
            except OSError, e:
                if e.errno == 2: 
                    log.debug("%s: %s" % (e.strerror, e.filename))
                else: 
                    raise e
        cache.cleanCache()


    def getGraph(self, id, ftype, REQUEST):
        """get a previously generated graph"""
        cache = self.setupCache()
        ftype = ftype.lower()
        mimetype = mimetypes.guess_type('.%s'%ftype)[0]
        if not mimetype: mimetype = 'image/%s' % ftype
        if REQUEST:
            response = REQUEST.RESPONSE
            response.setHeader('Content-Type', mimetype)
        return cache.checkCache(id)


InitializeClass(RenderServer)
