#! /usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = """zenrender

Listens in order to process RRD files to generate graphs
or retrieve data from a remote collector.
"""

import logging
log = logging.getLogger("zen.zenrender")

import mimetypes
import socket
import xmlrpclib

import Globals
import zope.interface

from twisted.web import resource, server
from twisted.internet import reactor

from Products.ZenCollector.daemon import CollectorDaemon
from Products.ZenCollector.interfaces import ICollectorPreferences,\
                                             ICollector
from Products.ZenCollector.tasks import NullTaskSplitter

# Invalidation issues arise if we don't import
from Products.ZenCollector.services.config import DeviceProxy

from Products.ZenRRD.RenderServer import RenderServer
from Products.ZenUtils.Utils import ipv6_available


class ZenRenderPreferences(object):
    zope.interface.implements(ICollectorPreferences)

    def __init__(self):
        """
        Constructs a new preferences instance and
        provides default values for needed attributes.
        """
        self.collectorName = "zenrender"
        self.configCycleInterval = 20 # minutes
        self.cycleInterval = 5 * 60 # seconds
        self.configurationService = 'Products.ZenHub.services.RenderConfig'

        # Will be filled in based on buildOptions
        self.options = None

    def buildOptions(self, parser):
        # Remove device option
        parser.remove_option('--device')

        # Add options
        parser.add_option('--http-port', type='int',
                          dest='httpport',
                          default= 8091,
                          help='Port zenrender listens on for HTTP'
                          'render requests. Default is %default.')

    def postStartup(self):
        """
        Listen for HTTP requests for RRD data or graphs.
        """
        self._daemon = zope.component.getUtility(ICollector)

        # Start listening for HTTP requests
        httpPort = self. _daemon.options.httpport
        collector = self._daemon.options.monitor
        log.info("Starting %s zenrender webserver on port %s",
                      collector, httpPort)
        renderer = HttpRender(collector)
        interface = '::' if ipv6_available() else ''
        reactor.listenTCP(httpPort, server.Site(renderer), interface=interface)

        # Add remote_ methods from renderer directly to the daemon
        for name in dir(renderer):
            if name.startswith('remote_'):
                func = getattr(renderer, name)
                setattr(self._daemon, name, func)


class HttpRender(resource.Resource):
    isLeaf = True

    def __init__(self, collectorName):
        self.log = log
        self._daemon = zope.component.getUtility(ICollector)
        self.collectorName = collectorName
        self.rs = RenderServer(collectorName)

    def remote_render(self, *args, **kw):
        return self.rs.render(*args, **kw)

    def remote_packageRRDFiles(self, *args, **kw):
        return self.rs.packageRRDFiles(*args, **kw)

    def remote_unpackageRRDFiles(self, *args, **kw):
        return self.rs.unpackageRRDFiles(*args, **kw)

    def remote_receiveRRDFiles(self, *args, **kw):
        return self.rs.receiveRRDFiles(*args, **kw)

    def remote_sendRRDFiles(self, *args, **kw):
        return self.rs.sendRRDFiles(*args, **kw)

    def remote_moveRRDFiles(self, *args, **kw):
        return self.rs.moveRRDFiles(*args, **kw)

    def remote_deleteRRDFiles(self, *args, **kw):
        return self.rs.deleteRRDFiles(*args, **kw)

    def remote_plugin(self, *args, **kw):
        return self.rs.plugin(*args, **kw)

    def remote_summary(self, *args, **kw):
        return self.rs.summary(*args, **kw)

    def remote_fetchValues(self, *args, **kw):
        return self.rs.fetchValues(*args, **kw)

    def remote_currentValues(self, *args, **kw):
        return self.rs.currentValues(*args, **kw)

    def _showHelp(self):
        """
        When someone hits the HTTP port directly, give them
        something other than a traceback.
        """
        helpText = [ """<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">
<html><title>zenrender Help</title>
<body>
<h3>This zenrender is for collector: %s</h3>
<h3>About zenrender</h3>
<p>The zenrender daemon receives calls from zenhub (or in some
special cases, by a browser directly) and given a request,
creates a graph of RRD data or returns back RRD information.
This daemon is not meant to be browsed directly by users.</p>
<p>A zenrender daemon should only respond to requests for
the remote collector with which it is associated.  This
zenrender daemon is registered with the '%s' collector.</p>
""" % (self.collectorName, self.collectorName)]

        methods = []
        for name in dir(self):
            if not name.startswith('remote_'):
                continue

            name = name.replace('remote_', '')
            docs = getattr(self.rs, name).__doc__
            docs = docs if docs is not None else ''
            methods.append( (name, docs) )

        # Insert table of methods
        helpText.append("""<table border='1'>
<caption>zenrender Methods</caption>
<tr><th>Method Name</th><th>Description</th></tr>""")
        for name, docs in sorted(methods):
            helpText.append("<tr><td>%s</td> <td><pre>%s</pre></td></tr>" % (
                            name, docs))
        helpText.append("</table>")

        # Drop in the trailer
        helpText.append("""</body></html>""")
        return '\n'.join(helpText)

    def render_GET(self, request):
        """
        Respond to HTTP GET requests
        """
        args = request.args.copy()
        for k, v in args.items():
            if len(v) == 1:
                args[k] = v[0]
        command = request.postpath[-1]
        self.log.debug("Processing %s request from %s", command,
                       request.getClientIP())
        if command == '':
            return self._showHelp()

        args.setdefault('ftype', 'PNG')
        ftype = args['ftype']
        del args['ftype']
        mimetype = mimetypes.guess_type('x.%s' % ftype)[0]
        if mimetype is None:
            mimetype = 'image/%s' % ftype.lower()
        request.setHeader('Content-type', mimetype)
        request.setHeader('Pragma', 'no-cache')
        # IE specific cache headers see http://support.microsoft.com/kb/234067/EN-US
        request.setHeader('Cache-Control', 'no-cache, no-store')
        request.setHeader('Expires', '-1')
        functor = getattr(self._daemon, 'remote_' + command, None)
        if functor:
            return functor(**args)

        # Ignore trash and log error messages
        if command not in ('favicon.ico',):
            self.log.error("Received a bad request: %s", command)
        return ''

    def render_POST(self, request):
        """
        Respond to HTTP POST requests (eg XML-RPC requests)
        """
        content = request.content.read()
        args, command = xmlrpclib.loads(content)
        self.log.debug("Processing %s request from %s" % (command,request.getClientIP()))
        request.setHeader('Content-type', 'text/xml')
        functor = getattr(self._daemon, 'remote_' + command, None)
        if functor and isinstance(args, (tuple, list, dict)):
            if isinstance(args, (tuple, list)):
                result = functor(*args)
            elif isinstance(args, dict):
                result = functor(**args)
            response = xmlrpclib.dumps((result,),
                methodresponse=True, allow_none=True)
            return response

        self.log.error("Received a bad request: %s", command)
        return ''


if __name__ == '__main__':
    myPreferences = ZenRenderPreferences()
    myTaskSplitter = NullTaskSplitter()
    daemon = CollectorDaemon(myPreferences, myTaskSplitter)
    daemon.run()
