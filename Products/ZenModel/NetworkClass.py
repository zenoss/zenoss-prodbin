#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""NetworkClass

The ipnetwork classification class.  default identifiers, screens,
and data collectors live here.

$Id: NetworkClass.py,v 1.16 2004/04/07 19:55:01 edahl Exp $"""

__version__ = "$Revision: 1.16 $"[11:-2]

from Globals import InitializeClass
from OFS.Folder import Folder
from Globals import DTMLFile
from AccessControl import ClassSecurityInfo

from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from SearchUtils import makeConfmonLexicon, makeIndexExtraParams
from Classification import Classification
from IpNetwork import manage_addIpNetwork

def manage_addNetworkClass(context, id, title = None, REQUEST = None):
    """make a device class"""
    dc = NetworkClass(id, title)
    context._setObject(id, dc)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addNetworkClass = DTMLFile('dtml/addNetworkClass',globals())

class NetworkClass(Classification, Folder):
    portal_type = meta_type = "NetworkClass"
    manage_main = Folder.manage_main
    manage_options = Folder.manage_options
    sub_classes = ('IpNetwork', 'IpAddress') 

    class_default_catalog = 'ipSearch'

    factory_type_information = ( 
        { 
            'id'             : 'NetworkClass',
            'meta_type'      : 'NetworkClass',
            'description'    : """NetworkClass class""",
            'icon'           : 'NetworkClass_icon.gif',
            'product'        : 'Confmon',
            'factory'        : 'manage_addNetworkClass',
            'immediate_view' : 'viewNetworkClassOverview',
            'actions'        :
            ( 
                { 'id'            : 'view'
                , 'name'          : 'View'
                , 'action'        : 'viewNetworkClassOverview'
                , 'permissions'   : ("View", )
                , 'visible'       : 0
                },
            )
          },
        )


    security = ClassSecurityInfo()
    
    def createCatalog(self):
        """make the catalog for device searching"""
        from Products.ZCatalog.ZCatalog import manage_addZCatalog
        manage_addZCatalog(self, self.class_default_catalog, 
                            self.class_default_catalog)
        zcat = self._getOb(self.class_default_catalog)
        makeConfmonLexicon(zcat)
        zcat.addIndex('id', 'ZCTextIndex', 
                        extra=makeIndexExtraParams('id'))
        zcat.addColumn('getPrimaryUrlPath')
    
    
    security.declareProtected('Change Network', 'addSubNetwork')
    def addSubNetwork(self, id, netmask=24):
        """add subnetwork to this network and return it"""
        manage_addIpNetwork(self,id,netmask)
        return self._getOb(id) 


    security.declareProtected('View', 'getSubNetwork')
    def getSubNetwork(self, ip):
        """get an ip on this network"""
        return self._getOb(ip,None)

    
InitializeClass(NetworkClass)
