#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""ProductClass

The product classification class.  default identifiers, screens,
and data collectors live here.

$Id: ProductClass.py,v 1.10 2004/03/26 23:58:44 edahl Exp $"""

__version__ = "$Revision: 1.10 $"[11:-2]

from Globals import InitializeClass
from OFS.Folder import Folder
from Globals import DTMLFile

from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from Classification import Classification

def manage_addProductClass(context, id, title = None, REQUEST = None):
    """make a device class"""
    dc = ProductClass(id, title)
    context._setObject(id, dc)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addProductClass = DTMLFile('dtml/addProductClass',globals())

class ProductClass(Classification, Folder):
    meta_type = "ProductClass"
    manage_main = Folder.manage_main
    manage_options = Folder.manage_options


    def getModelProduct(self, manufacturer, model):
        """get or create a hardware object and like it to its manufacturer"""
        from Products.ZenModel.ProductClass import manage_addProductClass
        from Products.ZenModel.Hardware import manage_addHardware
        from Products.ZenModel.Company import manage_addCompany
        
        companyObj = self.getDmdRoot("Companies").getCompany(manufacturer)
        hardwareOrg = self.getDmdRoot("Products").Hardware
        if not hasattr(hardwareOrg, manufacturer):
            manage_addProductClass(hardwareOrg, manufacturer)
        manufObj = hardwareOrg._getOb(manufacturer)
        if not hasattr(manufObj, model):
            manage_addHardware(manufObj, model)
        modelObj = manufObj._getOb(model)
        if not companyObj.products.hasobject(modelObj):
            companyObj.addRelation("products", modelObj)
        return modelObj 


    def getSoftwareProduct(self, manufacturer, name, version=""):
        """get or create a software object and like it to its manufacturer"""
        from Products.ZenModel.ProductClass import manage_addProductClass
        from Products.ZenModel.Software import manage_addSoftware
        from Products.ZenModel.Company import manage_addCompany

        companyObj = self.getDmdRoot("Companies").getCompany(manufacturer)
        softwareOrg = self.getDmdRoot("Products").Software
        if not hasattr(softwareOrg, manufacturer):
            manage_addProductClass(softwareOrg, manufacturer)
        manufObj = softwareOrg._getOb(manufacturer)
        if not hasattr(manufObj, name):
            manage_addHardware(manufObj, name)
        softwareObj = manufObj._getOb(name)
        if version: softwareObj.version = version
        if not companyObj.products.hasobject(softwareObj):
            companyObj.addRelation("products", softwareObj)
        return softwareObj
        

InitializeClass(ProductClass)
