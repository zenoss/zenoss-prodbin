##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

import io
import json
import os
import re

import six

from OFS.interfaces import IApplication
from Products.Five.browser import BrowserView
from Products.Five.viewlet.manager import ViewletManagerBase
from zope.component import getGlobalSiteManager
from zope.interface import implementer, Interface
from zope.publisher.interfaces.browser import IDefaultBrowserLayer

from Products.ZenUtils.CSEUtils import getCSEConf

from .interfaces import IHeadExtraManager

_JSB_SPEC = None
_RESOURCE_ROOT_PATH = os.path.join(os.path.dirname(__file__), "resources")


def hasCompiledJavascript():
    spec = _get_jsb_spec()
    deployDir = spec["deployDir"]
    filename = os.path.join(
        _RESOURCE_ROOT_PATH, deployDir, spec["pkgs"][0]["file"]
    )
    return os.path.exists(filename)


def _get_jsb_spec():
    global _JSB_SPEC

    if _JSB_SPEC is None:
        filename = os.path.join(_RESOURCE_ROOT_PATH, "builder.jsb2")
        with open(filename, "r") as fp:
            _JSB_SPEC = json.load(fp, object_hook=_as_bytes)

    return _JSB_SPEC


def _as_bytes(data):
    if isinstance(data, dict):
        return {str(k): _as_bytes(v) for k, v in data.iteritems()}
    elif isinstance(data, list):
        return [_as_bytes(v) for v in data]
    elif isinstance(data, six.text_type):
        return bytes(data)
    else:
        return data


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
    gsm.registerAdapter(
        CSEShortcut, (IApplication, IDefaultBrowserLayer), Interface, czID
    )


def get_js_file_list(pkg='Zenoss Application'):
    """
    Parse the JSBuilder2 config file to get a list of file names in the same
    order as that used by JSBuilder to generate its version.
    """
    paths = []
    spec = _get_jsb_spec()
    for p in spec["pkgs"]:
        if p["name"] == pkg:
            for f in p["fileIncludes"]:
                newpath = re.sub("^resources", "zenui", f["path"])
                paths.append(newpath + f["text"])
    return [str(path) for path in paths]


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
        self.request.response.setHeader("Content-Type", "text/javascript")
        sink = io.BytesIO()
        for p in get_js_file_list():
            fn = os.path.join(_RESOURCE_ROOT_PATH, p)
            with open(fn) as fp:
                sink.write(fp.read())
        try:
            return sink.getvalue()
        finally:
            sink.close()


@implementer(IHeadExtraManager)
class HeadExtraManager(ViewletManagerBase):
    """
    Simple viewlet manager allowing people to plug into <head>.
    """
