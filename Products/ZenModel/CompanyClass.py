#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""CompanyClass

The company classification class.  default identifiers and screens,
live here.

$Id: CompanyClass.py,v 1.10 2004/04/22 02:14:12 edahl Exp $"""

__version__ = "$Revision: 1.10 $"[11:-2]

import logging

from Globals import InitializeClass
from OFS.Folder import Folder
from Globals import DTMLFile

from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from Classification import Classification

def manage_addCompanyClass(context, idREQUEST = None):
    """make a company class"""
    cc = CompanyClass(id)
    context._setObject(id, cc)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 


addCompanyClass = DTMLFile('dtml/addCompanyClass',globals())


class CompanyClass(Classification, Folder):
    meta_type = "CompanyClass"
    manage_main = Folder.manage_main
    manage_options = Folder.manage_options
    sub_classes = ('CompanyClass', 'Company') 


    def getCompany(self, companyName):
        """get or create and return a company object"""
        from Products.ZenModel.Company import manage_addCompany
        if not hasattr(self, companyName):
            logging.info("Creating company %s" % companyName)
            manage_addCompany(self, companyName)
        return self._getOb(companyName)
               

    def getCompanyNames(self):
        """return list of all companies"""
        cnames = [""]
        cnames.extend(self.objectIds(spec=("Company")))
        return cnames


    def getProductNames(self, companyName):
        """return a list of all products this company makes"""
        prods = [""]
        if hasattr(self, companyName):
            company = self.getCompany(companyName)
            prods.extend(map(lambda x: x.getId(),
                company.products.objectValuesAll()))
        prods.sort()
        return prods


InitializeClass(CompanyClass)
