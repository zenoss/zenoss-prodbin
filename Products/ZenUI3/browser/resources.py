##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os
import re
import json
import logging
import Globals
from zope.interface import implements
from Products.Five.browser import BrowserView
from Products.Five.viewlet.manager import ViewletManagerBase
from Products.ZenUI3.browser.interfaces import IHeadExtraManager

_MISSING_JS_FILE_MESSAGE="""
************************************************************
The compressed javascript file %s
does not exist.  Zenoss will still run but UI performance is 
HEAVILY DEGRADED.  Please fix by running inst/buildjs.sh. 
************************************************************"""

def _checkForCompiledJSFile():
    COMPILED_JS_FILE = os.path.join(os.path.dirname(__file__), 
                                'resources/js/deploy/zenoss-compiled.js')
    jsFileExists =  os.path.exists(COMPILED_JS_FILE)
    if not Globals.DevelopmentMode and not jsFileExists:
        logging.getLogger().warning(_MISSING_JS_FILE_MESSAGE 
                                    % COMPILED_JS_FILE)
    return jsFileExists

JSBFILE = os.path.join(os.path.dirname(__file__), 'zenoss.jsb2')
COMPILED_JS_EXISTS = _checkForCompiledJSFile()

class ExtJSShortcut(BrowserView):
    def __getitem__(self, name):
        self.request.response.enableHTTPCompression(self.request)
        return self.context.unrestrictedTraverse('++resource++extjs')[name]


class ZenUIResourcesShortcut(BrowserView):
    def __getitem__(self, name):
        self.request.response.enableHTTPCompression(self.request)
        return self.context.unrestrictedTraverse('++resource++zenui')[name]


def get_js_file_list(pkg='Zenoss Application'):
    """
    Parse the JSBuilder2 config file to get a list of file names in the same
    order as that used by JSBuilder to generate its version.
    """
    jsb = open(JSBFILE)
    paths = []
    try:
        cfg = json.load(jsb)
        for p in cfg['pkgs']:
            if p['name']==pkg:
                for f in p['fileIncludes']:
                    path = re.sub('^resources', 'zenui', f['path'])
                    paths.append(path + f['text'])
    finally:
        jsb.close()
    return [ str(path) for path in paths ]


class PIEdotHTC(BrowserView):
    def __call__(self):
        self.request.response.setHeader('Content-Type', 'text/x-component')
        with open(os.path.join(os.path.dirname(__file__), 'PIE.htc')) as f:
            return f.read()


class ZenossJavaScript(BrowserView):
    """
    When Zope is in debug mode, we want to use the development JavaScript
    source files, so we don't have to make changes to a single huge file. When
    Zope is in production mode, we want a single minified file.  If Zope is
    in production mode and the compressed file is not available, we will use
    the source files instead of just giving up.
    """
    def __call__(self):
        self.request.response.setHeader('Content-Type', 'text/javascript')
        self.request.response.enableHTTPCompression(self.request)
        if Globals.DevelopmentMode or not COMPILED_JS_EXISTS:
            return self.dev()
        else:
            return self.production()

    def dev(self):
        """
        Read in the files in the same order as JSBuilder does when creating the
        minified version, concatenate them, and returnt the output.
        """
        src = []
        for p in get_js_file_list():
            fob = self.context.unrestrictedTraverse(p)
            src.append(fob.GET())
        return '\n'.join(src)

    def production(self):
        """
        Redirect to the minified file containing all Zenoss js.
        """
        self.request.RESPONSE.redirect('/++resource++zenui/js/deploy/zenoss-compiled.js')


class HeadExtraManager(ViewletManagerBase):
    """
    Simple viewlet manager allowing people to plug into <head>.
    """
    implements(IHeadExtraManager)
