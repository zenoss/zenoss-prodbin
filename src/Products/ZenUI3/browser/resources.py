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
from zope.interface import implements
from Products.Five.browser import BrowserView
from Products.Five.viewlet.manager import ViewletManagerBase
from Products.ZenUI3.browser.interfaces import IHeadExtraManager
from Products.ZenUtils.CSEUtils import getCSEConf
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from OFS.interfaces import IApplication
from zope.interface import Interface
from zope.component import getGlobalSiteManager

def _checkForCompiledJSFile():
    COMPILED_JS_FILE = os.path.join(os.path.dirname(__file__), 
                                'resources/js/deploy/zenoss-compiled.js')
    return os.path.exists(COMPILED_JS_FILE)

JSBFILE = os.path.join(os.path.dirname(__file__), 'zenoss.jsb2')
COMPILED_JS_EXISTS = _checkForCompiledJSFile()

class ExtJSShortcut(BrowserView):
    def __getitem__(self, name):
        return self.context.unrestrictedTraverse('++resource++extjs')[name]


class ZenUIResourcesShortcut(BrowserView):
    def __getitem__(self, name):
        return self.context.unrestrictedTraverse('++resource++zenui')[name]


class CSEShortcut(BrowserView):
    def __getitem__(self, name):
        if not name:
            return self.context.dmd
        return self.context[name]

czID = getCSEConf().get('virtualroot', '')
if czID:
    czID = czID.replace('/','') #remove slash
    gsm = getGlobalSiteManager()
    gsm.registerAdapter(CSEShortcut, (IApplication, IDefaultBrowserLayer), Interface, czID)

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
    Reads in the files in the same order as JSBuilder does when creating the
    minified version of the Zenoss JavaScript, concatenates them, and returns
    the output.
    """
    def __call__(self):
        self.request.response.setHeader('Content-Type', 'text/javascript')
        src = []
        for p in get_js_file_list():
            fob = self.context.unrestrictedTraverse(p)
            src.append(fob.GET())
        return '\n'.join(src)


class HeadExtraManager(ViewletManagerBase):
    """
    Simple viewlet manager allowing people to plug into <head>.
    """
    implements(IHeadExtraManager)
