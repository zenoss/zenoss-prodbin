#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""SystemClass

The system classification class.  default identifiers, screens,
and data collectors live here.

$Id: SystemClass.py,v 1.34 2004/04/09 00:34:39 edahl Exp $"""

__version__ = "$Revision: 1.34 $"[11:-2]

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from OFS.Folder import Folder
from Globals import DTMLFile

from Products.CMFCore import permissions

from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from SearchUtils import makeConfmonLexicon, makeIndexExtraParams
from Classification import Classification

def manage_addSystemClass(context, id, title = None, REQUEST = None):
    """make a device class"""
    dc = SystemClass(id, title)
    context._setObject(id, dc)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addSystemClass = DTMLFile('dtml/addSystemClass',globals())

class SystemClass(Classification, Folder):
    portal_type = meta_type = "SystemClass"
    manage_main = Folder.manage_main
    manage_options = Folder.manage_options
    class_default_catalog = "systemSearch"

    _properties = Classification._properties + (
                )
    
    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'id'             : 'SystemClass',
            'meta_type'      : 'SystemClass',
            'description'    : """SystemClass class""",
            'icon'           : 'SystemClass_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addSystemClass',
            'immediate_view' : 'classList',
            'actions'        :
            ( 
                { 'id'            : 'view'
                , 'name'          : 'View'
                , 'action'        : 'viewSystemClassOverview'
                , 'permissions'   : (
                  permissions.View, )
                , 'visible'       : 0
                },
            )
          },
        )
    

    security = ClassSecurityInfo()

    def __init__(self, id, title=None, prodStateConversions=[]):
        '''constructor'''
        Classification.__init__(self, id, title)
       

    def getSystem(self, path):
        """get or create a system from a system path"""
        from Products.ZenModel.System import manage_addSystem
        path = self.zenpathsplit(path)
        if path[0] != "Systems": path.insert(0, "Systems")
        name = self.zenpathjoin(path)
        sysObj = self.getHierarchyObj(self.getDmd(), name,
                                manage_addSystem,
                                relpath='subsystems')
        return sysObj


    def getSystemNames(self):
        """return a list of all the system paths"""
        sysnames = ["",]
        for system in self.objectValues():
            sysnames.extend(system.getSystemNames())
        sysnames.sort()        
        return sysnames


    security.declareProtected('View', 'convertProdState')
    def convertProdState(self, prodState):
        '''convert a numeric production state to a
        textual representation using the prodStateConversions
        map'''
        
        if self.prodStateConversions:
            for line in self.prodStateConversions:
                line = line.rstrip()
                (sev, num) = line.split(':')
                if int(num) == prodState:
                    return sev
        return "Unknown"

    def getSubSystems(self):
        """get all the systems under this system class instance"""
        return self.getSubObjects(self.filter, self.decend)


    def decend(self, obj):
        from Products.ZenModel.System import System
        return (obj.getId() == "subsystems" 
                or isinstance(obj, System)
                or isinstance(obj, SystemClass))

    def filter(self, obj):
        from Products.ZenModel.System import System
        return isinstance(obj, System)
      

InitializeClass(SystemClass)
