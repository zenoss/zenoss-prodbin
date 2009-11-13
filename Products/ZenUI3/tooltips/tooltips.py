import re
import urllib
import os.path
from xml.dom import minidom
from zope.i18n.negotiator import negotiator
from Products.Five.browser import BrowserView
from Products.ZenUtils.json import json

_valpat = re.compile(r'<[^<>]+>(.*)</[^<>]+>', re.M|re.S)

DATAPATH = os.path.join(os.path.dirname(__file__), 'data')

class _TooltipCatalog(object):
    """
    Store the data pulled in from XML. This is a singleton and should not be
    instantiated directly.
    """
    _catalog = None

    def __init__(self):
        self._catalog = {}
        self.reload()

    def add(self, lang, view, tip):
        self._catalog.setdefault(view, {}).setdefault(lang, []).append(tip)

    def reload(self):
        """
        Read in tooltips from XML files.
        """
        def _load(_none, path, fnames):
            lang = path.rsplit('/', 1)[-1]
            for f in fnames:
                if not f.endswith('.xml'):
                    continue
                view = f[:-4]
                doc = minidom.parse(f)
                for tip in doc.getElementsByTagName('tooltip'):
                    d = {}
                    for node in tip.childNodes:
                        if isinstance(node, minidom.Text): continue
                        result = _valpat.search(node.toxml())
                        value = result.groups()[0].strip()
                        name = node.tagName
                        if name in ('autoHide', 'closable', 'draggable'):
                            value = eval(value)
                        elif name=='width':
                            value = int(value)
                        d[name] = value
                    if 'autoHide' in d:
                        if d['autoHide']:
                            d['closable'] = False
                        else:
                            d['closable'] = True
                    self.add(lang, view, d)
                doc.unlink()
        os.path.walk(DATAPATH, _load, None)

    def tips(self, view, lang="en"):
        """
        Look up the tooltips for a given screen and language.
        """
        return self._catalog.get(view, {}).get(lang, [])[:]

    def langs(self, view):
        """
        Returns a list of languages available for a given screen.
        """
        return self._catalog.get(view, {}).keys()

TooltipCatalog = _TooltipCatalog()


class Tooltips(BrowserView):
    def __call__(self):
        results = []
        viewname = self.request['HTTP_REFERER'].rsplit('/', 1)[-1]
        lang = negotiator.getLanguage(TooltipCatalog.langs(viewname),
                                      self.request)
        tips = TooltipCatalog.tips(viewname, lang)
        tpl = "Zenoss.registerTooltip(%s);"
        for tip in tips:
            results.append(tpl % json(tip))
        return "Ext.onReady(function(){%s})" % '\n'.join(results)
