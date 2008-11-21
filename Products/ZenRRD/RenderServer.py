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

Frontend that passes RRD graph options to rrdtool to render,
and then returns an URL to access the rendered graphic file.
"""

import os
import time
import logging
import urllib
import zlib
import mimetypes

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from Globals import DTMLFile
from sets import Set

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
    """
    Make a RenderServer
    """
    rs = RenderServer(id)
    context._setObject(id, rs)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
                                     

addRenderServer = DTMLFile('dtml/addRenderServer',globals())


class RenderServer(RRDToolItem):
    """
    Base class for turning graph requests into graphics.
    NB: Any log messages get logged into the event.log file.
    """

    meta_type = "RenderServer"

    cacheName = 'RRDRenderCache'
    
    security = ClassSecurityInfo()

    def __init__(self, id, tmpdir = '/tmp/renderserver', cachetimeout=300):
        self.id = id
        self.tmpdir = tmpdir
        self.cachetimeout = cachetimeout


    def removeInvalidRRDReferences(self, cmds):
        """
        Check the cmds list for DEF commands.  For each one check that the rrd
        file specified actually exists.  Return a list of commands which
        excludes commands referencing or depending on non-existent RRD files.

        @param cmds: list of RRD commands
        @return: sanitized list of RRD commands
        """
        newCmds = []
        badNames = Set()
        for cmd in cmds:
            if cmd.startswith('DEF:'):
                # Check for existence of the RRD file
                vName, rrdFile = cmd.split(':')[1].split('=', 1)
                if not os.path.isfile(rrdFile):
                    badNames.add(vName)
                    parts = rrdFile.split('/')
                    try:
                        devIndex = parts.index('Devices') + 1
                    except ValueError:
                        devIndex = -1
                    devName = devIndex > 0 and parts[devIndex] or ''
                    compIndex = len(parts) - 2
                    compName = compIndex > devIndex and parts[compIndex] or ''
                    dpName = parts[-1].rsplit('.', 1)[0]
                    desc = ' '.join([p for p in (devName,compName,dpName) if p])
                    newCmds.append('COMMENT:MISSING RRD FILE\: %s' % desc)
                    continue

            elif cmd.startswith('VDEF:') or cmd.startswith('CDEF:'):
                vName, expression = cmd.split(':', 1)[1].split('=', 1)
                if Set(expression.split(',')) & badNames:
                    badNames.add(vName)
                    continue

            elif not cmd.startswith('COMMENT'):
                try:
                    vName = cmd.split(':')[1].split('#')[0]
                except IndexError:
                    vName = None
                if vName in badNames:
                    continue
            newCmds.append(cmd)
        return newCmds


    security.declareProtected('View', 'render')
    def render(self, gopts=None, start=None, end=None, drange=None, 
               remoteUrl=None, width=None, ftype='PNG', getImage=True, 
               graphid='', comment=None, ms=None, REQUEST=None):
        """
        Render a graph and return it

        @param gopts: RRD graph creation options
        @param start: requested start of data to graph
        @param end: requested start of data to graph
        @param drange: min/max values of the graph
        @param remoteUrl: if the RRD is not here, where it lives
        @param width: size of graphic to create
        @param ftype: file type of graphic (eg PNG)
        @param getImage: return the graph or a script location
        @param graphid: (hopefully) unique identifier of a graph
        @param comment: RRD graph comment
        @param ms: a timestamp used to force IE to reload images
        @param REQUEST: URL-marshalled object containg URL options
        @return: graph or script location
        """
        gopts = zlib.decompress(urlsafe_b64decode(gopts))
        gopts = gopts.split('|')
        gopts = self.removeInvalidRRDReferences(gopts)
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
                log.debug("RRD graphing options: %r", (gopts,))
                try:
                    rrdtool.graph(*gopts)
                except Exception, ex:    
                    if ex.args[0].find('No such file or directory') > -1:
                        return None
                    log.exception("Failed to generate a graph")
                    log.warn(" ".join(gopts))
                    return None

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
        Else delete all RRD files associated with the given device.

        @param device: device name
        @param datasource: RRD datasource (DS) name
        @param datapoint: RRD datapoint name (lives in a DS)
        @param remoteUrl: if the RRD is not here, where it lives
        @param REQUEST: URL-marshalled object containg URL options
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
        """
        Tar up RRD files into a nice, neat package

        @param device: device name
        @param REQUEST: URL-marshalled object containg URL options
        """
        srcdir = performancePath('/Devices/%s' % device)
        tarfilename = '%s/%s.tgz' % (self.tmpdir, device)
        log.debug( "tarring up %s into %s" % ( srcdir, tarfilename ))
        tar = tarfile.open(tarfilename, "w:gz")
        for file in os.listdir(srcdir):
            tar.add('%s/%s' % (srcdir, file), '/%s' % os.path.basename(file))
        tar.close()

    def unpackageRRDFiles(self, device, REQUEST=None):
        """
        Untar a package of RRDFiles

        @param device: device name
        @param REQUEST: URL-marshalled object containg URL options
        """
        destdir = performancePath('/Devices/%s' % device)
        tarfilename = '%s/%s.tgz' % (self.tmpdir, device)
        log.debug( "Untarring %s into %s" % ( tarfilename, destdir ))
        tar = tarfile.open(tarfilename, "r:gz")
        for file in tar.getmembers():
            tar.extract(file, destdir)
        tar.close()

    def receiveRRDFiles(self, REQUEST=None):
        """
        Receive a device's RRD Files from another server
        This function is called by sendRRDFiles()

        @param REQUEST: 'tarfile', 'tarfilename'
        @type REQUEST: URL-marshalled parameters
        """
        tarfile = REQUEST.get('tarfile')
        tarfilename = REQUEST.get('tarfilename')
        log.debug( "Receiving %s ..." % ( tarfilename ))
        f=open('%s/%s' % (self.tmpdir, tarfilename), 'wb')
        f.write(urllib.unquote(tarfile))
        f.close()
                
    def sendRRDFiles(self, device, server, REQUEST=None):
        """
        Move a package of RRDFiles

        @param device: device name
        @param server: another RenderServer instance
        @param REQUEST: URL-marshalled object containg URL options
        """
        tarfilename = '%s.tgz' % device
        f=open('%s/%s' % (self.tmpdir, tarfilename), 'rb')
        tarfilebody=f.read()
        f.close()
        # urlencode the id, title and file
        params = urllib.urlencode({'tarfilename': tarfilename,
            'tarfile':tarfilebody})

        # send the file to Zope
        perfMon = self.dmd.getDmdRoot("Monitors").getPerformanceMonitor(server)
        if perfMon.renderurl.startswith('http'):
            remoteUrl = '%s/receiveRRDFiles' % (perfMon.renderurl)
            log.debug( "Sending %s to %s ..." % ( tarfilename, remoteUrl ))
            urllib.urlopen(remoteUrl, params)
            
    
    def moveRRDFiles(self, device, destServer, srcServer=None, REQUEST=None):
        """
        Send a device's RRD files to another server

        @param device: device name
        @param destServer: another RenderServer instance
        @param srcServer: another RenderServer instance
        @param REQUEST: URL-marshalled object containg URL options
        """
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
        """
        Render a custom graph and return it

        @param name: plugin name from Products/ZenRRD/plugins
        @return: graph or None
        """
        try:
            m = zenPath('Products/ZenRRD/plugins/%s.py' % name)
            log.debug( "Trying plugin %s to generate a graph..." % m )
            graph = None
            exec open(m)
            return graph
        except Exception, ex:
            log.exception("Failed generating graph from plugin %s" % name)
            raise


    security.declareProtected('GenSummary', 'summary')
    def summary(self, gopts):
        """
        Return summary information as a list but no graph

        @param gopts: RRD graph options
        @return: values from the graph
        """
        gopts.insert(0, '/dev/null') #no graph generated
        try:
            values = rrdtool.graph(*gopts)[2]
        except Exception, ex:
            if ex.args[0].find('No such file or directory') > -1:
                return None
            log.exception("Failed while generating summary")
            log.warn(" ".join(gopts))
            raise
        return values
        

    security.declareProtected('GenSummary', 'currentValues')
    def currentValues(self, paths):
        """
        Return the latest values recorded in the RRD file
        """
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
            log.exception("It appears that the rrdtool bindings are not installed properly.")

        except Exception, ex:
            if ex.args[0].find('No such file or directory') > -1:
                return None
            log.exception("Failed while generating current values")
            raise
        

    def rrdcmd(self, gopts, ftype='PNG'):
        """
        Generate the RRD command using the graphing options specified.

        @param gopts: RRD graphing options
        @param ftype: graphic file type (eg PNG)
        @return: RRD command usable on the command-line
        @rtype: string
        """
        filename, gopts = self._setfile(gopts, ftype)
        return "rrdtool graph " + " ".join(gopts)


    def graphId(self, gopts, drange, ftype):
        """
        Generate a graph id based on a hash of values

        @param gopts: RRD graphing options
        @param drange: min/max values of the graph
        @param ftype: graphic file's type (eg PNG)
        @return: An id for this graph usable in URLs
        @rtype: string
        """
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
        """
        Make a new cache if we need one
        """
        if not hasattr(self, '_v_cache') or not self._v_cache:
            tmpfolder = self.getPhysicalRoot().temp_folder
            if not hasattr(tmpfolder, self.cacheName):
                cache = PObjectCache(self.cacheName, self.cachetimeout)
                tmpfolder._setObject(self.cacheName, cache)
            self._v_cache = tmpfolder._getOb(self.cacheName)
        return self._v_cache


    def addGraph(self, id, filename):
        """
        Add a graph to temporary folder

        @param id: graph id
        @param filename: cacheable graphic file
        """
        cache = self.setupCache()
        graph = self._loadfile(filename)
        if graph: 
            cache.addToCache(id, graph)
            try: 
                os.remove(filename)
            except OSError, e:
                if e.errno == 2: 
                    log.debug("Unable to remove cached graph %s: %s" \
                        % (e.strerror, e.filename))
                else: 
                    raise e
        cache.cleanCache()


    def getGraph(self, id, ftype, REQUEST):
        """
        Get a previously generated graph

        @param id: graph id
        @param ftype: file type of graphic (eg PNG)
        @param REQUEST: graph id
        """
        cache = self.setupCache()
        ftype = ftype.lower()

        if REQUEST:
            mimetype = mimetypes.guess_type('.%s'%ftype)[0]
            if not mimetype:
                mimetype = 'image/%s' % ftype
            response = REQUEST.RESPONSE
            response.setHeader('Content-Type', mimetype)

        return cache.checkCache(id)


InitializeClass(RenderServer)
