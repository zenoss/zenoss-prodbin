from urlparse import urljoin

from zope.component import getGlobalSiteManager
from zope.interface import Interface
from zope.interface import implements

from Products.ZenUtils.GlobalConfig import getGlobalConfiguration


class IVirtualRoot(Interface):

    def get_prefix():
        """
        Return the virtual root path prefix configured.
        """

    def strip_virtual_root(url):
        """
        Strip the configured virtual root from the url provided.
        """

    def ensure_virtual_root(url):
        """
        Prefix the url provided with the configured virtual root.
        """


class CSEVirtualRoot(object):

    implements(IVirtualRoot)

    def __init__(self, prefix):
        if prefix:
            # Sanitize slashes
            prefix = '/%s' % prefix.strip('/')
        else:
            prefix = ""
        self._prefix = prefix

    def get_prefix(self):
        return self._prefix

    def ensure_virtual_root(self, url):
        if self._prefix and url.startswith('/'):
            url = urljoin(self._prefix, url.lstrip('/'))
        return url

    def strip_virtual_root(self, url):
        if self._prefix and url.startswith(self._prefix + '/'):
            url = url[len(self._prefix):]
        return url


def register_cse_virtual_root():
    config = getGlobalConfiguration()
    prefix = config.get('virtual-root', '')
    gsm = getGlobalSiteManager()
    gsm.registerUtility(CSEVirtualRoot(prefix), IVirtualRoot)


register_cse_virtual_root()
