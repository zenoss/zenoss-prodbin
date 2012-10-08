##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__="""RenderServer

Frontend that passes RRD graph options to rrdtool to render,
and then returns an URL to access the rendered graphic file.
"""

import os
import time
import logging
import json
import urllib
import zlib
import mimetypes
import glob
import tarfile
import md5
import tempfile
from Products.ZenUtils import Map
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from Globals import DTMLFile

try:
    import rrdtool
except ImportError:
    pass

from base64 import b64encode, urlsafe_b64decode, urlsafe_b64encode
from urllib import urlencode

from Products.ZenRRD.RRDUtil import fixMissingRRDs
from Products.ZenUtils.Utils import zenPath, rrd_daemon_args, rrd_daemon_retry

from RRDToolItem import RRDToolItem

from Products.ZenModel.PerformanceConf import performancePath

log = logging.getLogger("zen.RenderServer")


def manage_addRenderServer(context, id, REQUEST = None):
    """
    Make a RenderServer
    """
    rs = RenderServer(id)
    context._setObject(id, rs)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')


addRenderServer = DTMLFile('dtml/addRenderServer',globals())

DEFAULT_TIMEOUT=300
_cache = Map.Locked(Map.Timed({}, DEFAULT_TIMEOUT))


class RenderServer(RRDToolItem):
    """
    Base class for turning graph requests into graphics.
    NB: Any log messages get logged into the event.log file.
    """

    meta_type = "RenderServer"

    cacheName = 'RRDRenderCache'

    security = ClassSecurityInfo()

    def __init__(self, id, tmpdir = '/tmp/renderserver', cachetimeout=DEFAULT_TIMEOUT):
        self.id = id
        self.tmpdir = tmpdir
        self.cachetimeout = cachetimeout


    security.declareProtected('View', 'render')
    def render(self, gopts=None, start=None, end=None, drange=None,
               remoteUrl=None, width=None, ftype='PNG', getImage=True,
               graphid='', comment=None, ms=None, remoteHost=None, REQUEST=None, zenrenderRequest=None):
        """
        Render a graph and return it

        @param gopts: RRD graph creation options
        @param start: requested start of data to graph
        @param end: requested start of data to graph
        @param drange: min/max values of the graph
        @param remoteUrl: if the RRD is not here, where it lives -DEPRECATED use remoteHost instead
        @param width: size of graphic to create
        @param ftype: file type of graphic (eg PNG)
        @param getImage: return the graph or a script location
        @param graphid: (hopefully) unique identifier of a graph
        @param comment: RRD graph comment
        @param ms: a timestamp used to force IE to reload images
        @param remoteHost: Forward current RRD request to renderserver at remoteHost. eg http://remotezenrender:8091/
        @param REQUEST: URL-marshalled object containg URL options
        @return: graph or script location
        """
        # gopts may have repeated url quoting, possibly from multiple hops thru remote zenhubs
        # extra quoting will create invalid zlib padding characters ('%3D' instead of '=')
        for tries in range(3):
            try:
                gopts = zlib.decompress(urlsafe_b64decode(gopts))
            except Exception:
                gopts = urllib.unquote(gopts)
            else:
                break

        comment = urllib.unquote(comment) if comment is not None else ''

        gopts = gopts.split('|')
        gopts = fixMissingRRDs(gopts)
        gopts.append('HRULE:INF#00000000')
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
            fd, filename = tempfile.mkstemp(dir=self.tmpdir, suffix=id)
            if remoteHost or remoteUrl:
                if remoteHost:
                    encodedOpts = urlsafe_b64encode(
                        zlib.compress('|'.join(gopts), 9))
                    params = {
                        'gopts': encodedOpts,
                        'drange': drange,
                        'width': width,
                    }
                    remote = "%s/render?%s" %(remoteHost, urlencode(params))
                else:
                    remote = remoteUrl
                f = open(filename, "w")
                response = urllib.urlopen(remote).read()
                f.write(response)
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
                if comment is not None:
                    gopts.insert(0, 'COMMENT:%s\\c' % comment)
                gopts.insert(0, '--end=%d' % end)
                gopts.insert(0, '--start=%d' % start)
                gopts.insert(0, filename)
                log.debug("RRD graphing options: %r", (gopts,))
                try:
                    @rrd_daemon_retry
                    def rrdtool_fn():
                        rrdtool.graph(*(gopts + list(rrd_daemon_args())))
                    rrdtool_fn()

                except Exception, ex:
                    if ex.args[0].find('No such file or directory') > -1:
                        return None
                    log.exception("Failed to generate a graph")
                    log.warn(" ".join(gopts))
                    return None

            self.addGraph(id, filename, fd)
            graph = self.getGraph(id, ftype, REQUEST)

        if getImage:
            return graph
        else:
            success = bool(graph)
            ret = {'success':success}
            if success:
                ret['data'] = b64encode(graph)

            if REQUEST:
                REQUEST.RESPONSE.setHeader('Content-Type', 'text/javascript')
            elif zenrenderRequest:
                zenrenderRequest.setHeader('Content-Type', 'text/javascript')
            return """Zenoss.SWOOP_CALLBACKS["%s"]('%s')""" % (graphid, json.dumps(ret))


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
        # If remoteUrl is specified, open/invoke that first because we
        # probably want to delete RRD files on some other machine.
        if remoteUrl:
            urllib.urlopen(remoteUrl)
        # Carry on with deleting local RRD files; however, if remoteUrl was
        # specified, then the devDir path (probably) doesn't exist on this
        # machine.
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
        if perfMon.getRemoteRenderUrl().startswith('http'):
            remoteUrl = '%s/receiveRRDFiles' % (perfMon.getRemoteRenderUrl())
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
            remoteUrl = '%s/moveRRDFiles?device=%s&destServer=%s' % (srcPerfMon.getRemoteRenderUrl(), device, destServer)
            urllib.urlopen(remoteUrl)

        else:
            self.packageRRDFiles(device, REQUEST)
            self.sendRRDFiles(device, destServer, REQUEST)
            if destPerfMon.getRemoteRenderUrl().startswith('http'):
                remoteUrl = '%s/unpackageRRDFiles?device=%s' % (destPerfMon.getRemoteRenderUrl(), device)
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
        except Exception:
            log.exception("Failed generating graph from plugin %s" % name)
            raise


    security.declareProtected('GenSummary', 'summary')
    def summary(self, gopts):
        """
        Return summary information as a list but no graph

        @param gopts: RRD graph options
        @return: values from the graph
        """
        gopts = fixMissingRRDs(gopts)
        gopts.insert(0, '/dev/null') #no graph generated
        log.debug("RRD summary options: %r", (gopts,))
        try:
            @rrd_daemon_retry
            def rrdtool_fn():
                return rrdtool.graph(*(gopts+list(rrd_daemon_args())))[2]
            values = rrdtool_fn()
        except Exception, ex:
            if ex.args[0].find('No such file or directory') > -1:
                return None
            log.exception("Failed while generating summary")
            log.warn(" ".join(gopts))
            raise
        return values


    security.declareProtected('GenSummary', 'fetchValues')
    def fetchValues(self, paths, cf, resolution, start, end=""):
        """
        Return the values recorded in the RRD file between the start and end period

        @param paths: path names to files
        @param cf: RRD consolidation function to use
        @param resolution: requested resolution of RRD data
        @param start: requested start of data to graph
        @param end: requested start of data to graph
        @return: values from the RRD files in the paths
        """
        if not end:
            end = "now"
        values = []
        try:
            for path in paths:
                @rrd_daemon_retry
                def rrdtool_fn():
                    try:
                        values.append(rrdtool.fetch(
                            path, cf, "-r %d" % resolution,
                            "-s %s" % start, "-e %s" % end,
                            *rrd_daemon_args()))

                    except rrdtool.error, ex:
                        if 'No such file or directory' in ex.message:
                            values.append(None)
                        else:
                            raise

                rrdtool_fn()
            return values
        except NameError:
            log.exception("It appears that the rrdtool bindings are not installed properly.")
        except Exception, ex:
            log.exception("Failed while generating current values")
            raise


    security.declareProtected('GenSummary', 'currentValues')
    def currentValues(self, paths):
        """
        Return the latest values recorded in the RRD file

        @param paths: path names to files
        @return: values from the RRD files in the path
        """
        try:
            def value(p):
                v = None
                info = None
                try:
                    @rrd_daemon_retry
                    def rrdtool_fn():
                        return rrdtool.info(p, *rrd_daemon_args())
                    info = rrdtool_fn()
                except Exception:
                    log.debug('%s not found' % p)
                if info:
                    last = info['last_update']
                    step = info['step']
                    gopts = ['/dev/null',
                             'DEF:x=%s:ds0:AVERAGE' % p,
                             'VDEF:v=x,LAST',
                             'PRINT:v:%.2lf',
                             '--start=%d'%(last-step),
                             '--end=%d'%last]
                    log.debug("RRD currentValue options: %r", (gopts,))
                    @rrd_daemon_retry
                    def rrdtool_fn():
                        return rrdtool.graph(*(gopts+list(rrd_daemon_args())))
                    v = rrdtool_fn()
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
            self._v_cache = _cache
            self._v_cache.map.timeout = self.cachetimeout
        return self._v_cache


    def addGraph(self, id, filename, fd):
        """
        Add a graph to temporary folder

        @param id: graph id
        @param filename: cacheable graphic file
        """
        cache = self.setupCache()
        graph = self._loadfile(filename)
        if graph:
            cache[id] = graph
            try:
                os.close(fd)
                os.remove(filename)
            except OSError, e:
                if e.errno == 2:
                    log.debug("Unable to remove cached graph %s: %s" \
                        % (e.strerror, e.filename))
                else:
                    raise e

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
            mimetype = mimetypes.guess_type('%s.%s' % (id, ftype))[0]
            if mimetype is None:
                mimetype = 'image/%s' % ftype
            response = REQUEST.RESPONSE
            response.setHeader('Content-Type', mimetype)
            response.setHeader('Pragma', 'no-cache')
            # IE specific cache headers
            response.setHeader('Cache-Control', 'no-cache, no-store')
            response.setHeader('Expires', '-1')
        return cache.get(id, None)

InitializeClass(RenderServer)
