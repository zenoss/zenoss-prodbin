#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""ReportClass

ReportClass groups different types of reports together

$Id: ReportClass.py,v 1.3 2004/04/22 15:33:44 edahl Exp $"""

__version__ = "$Revision: 1.3 $"[11:-2]

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from OFS.Folder import Folder
from Globals import DTMLFile

from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from Classification import Classification

def manage_addReportClass(context, id, title = None, REQUEST = None):
    """make a device class"""
    dc = ReportClass(id, title)
    context._setObject(id, dc)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addReportClass = DTMLFile('dtml/addReportClass',globals())

class ReportClass(Classification, Folder):
    portal_type = meta_type = "ReportClass"
    manage_main = Folder.manage_main
    manage_options = Folder.manage_options


    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'id'             : 'ReportClass',
            'meta_type'      : 'ReportClass',
            'description'    : """ReportClass class""",
            'icon'           : 'ReportClass_icon.gif',
            'product'        : 'Confmon',
            'factory'        : 'manage_addReportClass',
            'immediate_view' : 'viewReportClass',
            'actions'        :
            ( 
                { 'id'            : 'view'
                , 'name'          : 'View'
                , 'action'        : 'viewReportClass'
                , 'permissions'   : ( "View",)
                , 'visible'       : 0
                },
            )
          },
        )
    
    security = ClassSecurityInfo()

    def __init__(self, id, title=None):
        '''constructor'''
        Classification.__init__(self, id, title)
     
    security.declareProtected('Change Page Templates','pt_editAction')
    def pt_editAction(self, REQUEST, title, text, 
                        content_type, expand, description):
        
        self.description = description
        return ZopePageTemplate.pt_editAction(self, REQUEST, title, text,
                                            content_type, expand)


InitializeClass(ReportClass)
