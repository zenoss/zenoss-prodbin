import logging
log = logging.getLogger("zen.ZenossInfo")

from Globals import InitializeClass
from OFS.SimpleItem import SimpleItem
from AccessControl import ClassSecurityInfo
from Products.ZenModel.version import Current

def manage_addZenossInfo(context, id='ZenossInfo', REQUEST=None):
    """
    Provide an instance of ZenossInfo for the portal.
    """
    about = ZenossInfo(id)
    context._setObject(id, about)

    if REQUEST is not None:
        REQUEST.RESPONSE.redirect(context.absolute_url() +'/manage_main')

class ZenossInfo(SimpleItem):

    security = ClassSecurityInfo()

    def getAllVersions(self):
        """
        Return a list of version numbers for currently tracked component
        software.
        """
        vers = Current.getVersions()
        versions = [
            {'header': 'Zenoss', 'data': vers['Zenoss']},
            {'header': 'OS', 'data': vers['OS']},
            {'header': 'Zope', 'data': vers['Zope']},
            {'header': 'Python', 'data': vers['Python']},
            {'header': 'Database', 'data': vers['Database']},
            {'header': 'RRD', 'data': vers['RRD']},
            {'header': 'Twisted', 'data': vers['Twisted']},
            {'header': 'SNMP', 'data': vers['SNMP']},
        ]
        return versions
    security.declareProtected('View','getAllVersions')

    def getAllUptimes(self):
        """
        Return a list of daemons with their uptimes.
        """
        app = self.getPhysicalRoot()
        uptimes = []
        zope = {
            'header': 'Zope',
            'data': app.Control_Panel.process_time(),
        }
        uptimes.append(zope)
        return uptimes
    security.declareProtected('View','getAllUptimes')

InitializeClass(ZenossInfo)
