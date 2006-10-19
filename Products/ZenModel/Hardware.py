#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""Hardware

Hardware represents a hardware vendor's product.

$Id: Hardware.py,v 1.5 2003/03/08 18:34:24 edahl Exp $"""

__version__ = "$Revision: 1.5 $"[11:-2]

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from Products.ZenRelations.RelSchema import *

from MEProduct import MEProduct

def manage_addHardware(context, id, title = None, REQUEST = None):
    """make a Hardware"""
    d = Hardware(id, title)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addHardware = DTMLFile('dtml/addHardware',globals())

class Hardware(MEProduct):
    """Hardware object"""
    portal_type = meta_type = 'Hardware'

    tag = ""
    serialNumber = ""

    _properties = MEProduct._properties + (
        {'id':'tag', 'type':'string', 'mode':'w'},
        {'id':'serialNumber', 'type':'string', 'mode':'w'},
    )

    security = ClassSecurityInfo()

    security.declareProtected('Change Device', 'setProduct')
    def setProduct(self, productName,  manufacturer="Unknown", 
                    newProductName="", REQUEST=None, **kwargs):
        """Set the product class of this software.
        """
        if not manufacturer: manufacturer = "Unknown"
        if newProductName: productName = newProductName
        prodobj = self.getDmdRoot("Manufacturers").createHardwareProduct(
                                        productName, manufacturer, **kwargs)
        self.productClass.addRelation(prodobj)
        if REQUEST:
            REQUEST['message'] = ("Set Manufacturer %s and Product %s at time:" 
                                    % (manufacturer, productName))
            return self.callZenScreen(REQUEST)


    def setProductKey(self, prodKey):
        """Set the product class of this software by its productKey.
        """
        if prodKey:
            manufs = self.getDmdRoot("Manufacturers")
            prodobj = manufs.createHardwareProduct(prodKey)
            self.productClass.addRelation(prodobj)
        else:
            self.productClass.removeRelation()
    
    
    def getDeviceLink(self):
        return super(Hardware, self).getDeviceLink('deviceHardwareDetail')


InitializeClass(Hardware)
