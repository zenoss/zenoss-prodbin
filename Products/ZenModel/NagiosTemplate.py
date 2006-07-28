#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions
from Acquisition import aq_base

from Products.ZenRelations.RelSchema import *

from ZenModelRM import ZenModelRM
from NagiosCmd import NagiosCmd


def crumbspath(templ, crumbs, idx=-1):
    """Create the crumbs path for sub objects of an RRDTemplate.
    """
    dc = templ.deviceClass() 
    pt = "/nagiosConfig"
    if not dc: 
       dc = templ.getPrimaryParent()
       pt = "/objNagiosTemplate"
    url = dc.getPrimaryUrlPath()+pt
    if pt == "/objNagiosTemplate": 
        del crumbs[-2]
        idx = -1
    crumbs.insert(idx,(url,'NagConf'))
    return crumbs



def manage_addNagiosTemplate(context, id, REQUEST = None):
    """make a NagiosTemplate"""
    tt = NagiosTemplate(id)
    context._setObject(tt.id, tt)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')


class NagiosTemplate(ZenModelRM):

    description = ""

    _properties = (
        {'id':'description', 'type':'string', 'mode':'w'},
    )

    _relations =  (
        ("deviceClass", ToOne(ToManyCont, "DeviceClass", "nagiosTemplates")),
        ("nagiosCmds", ToManyCont(ToOne, "NagiosCmd", "nagiosTemplate")),
    )    

    factory_type_information = ( 
        { 
            'immediate_view' : 'viewNagiosTemplate',
            'actions'        :
            ( 
                { 'name'          : 'Nagios Config'
                , 'action'        : 'viewNagiosTemplate'
                , 'permissions'   : ( Permissions.view, )
                },
                { 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : ( Permissions.view, )
                },
            )
         },
        )
    
    security = ClassSecurityInfo()


    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object add ActionRules list.
        [('url','id'), ...]
        """
        crumbs = super(NagiosTemplate, self).breadCrumbs(terminator)
        return crumbspath(self, crumbs)


    def isEditable(self, context):
        """Is this template editable in context.
        """
        return (self.isManager() and 
                (context == self or self.id=='Device_Nagios'))

    
    def getNagiosTemplatePath(self):
        """Return the path on which this template is defined.
        """
        return self.getPrimaryParent().getPrimaryDmdId(subrel="nagiosTemplates")
   

    def getNagiosTemplatePathLink(self):
        """Return alink path on which this template is defined.
        """
        return "<a href='%s'>%s</a>" % (
                self.getPrimaryParent().getPrimaryUrlPath()+"/nagiosConfig", 
                self.getNagiosTemplatePath())
    
    
    security.declareProtected('Add DMD Objects', 'manage_addNagiosCmd')
    def manage_addNagiosCmd(self, id, REQUEST=None):
        """Add an NagiosCmd to this DeviceClass.
        """
        if not id: return self.callZenScreen(REQUEST)
        org = NagiosCmd(id)
        self.nagiosCmds._setObject(org.id, org)
        if REQUEST: return self.callZenScreen(REQUEST)
            

    def manage_deleteNagiosCmds(self, ids=(), REQUEST=None):
        """Delete NagiosCmds from this DeviceClass 
        (skips ones in other Classes)
        """
        if not ids: return self.callZenScreen(REQUEST)
        for id in ids:
            if (getattr(aq_base(self), 'nagiosCmds', False) 
                and getattr(aq_base(self.nagiosCmds),id,False)):
                self.nagiosCmds._delObject(id)
        if REQUEST: return self.callZenScreen(REQUEST)

    
    def manage_copyNagiosCmds(self, ids=(), REQUEST=None):
        """Put a reference to the objects named in ids in the clip board"""
        if not ids: return self.callZenScreen(REQUEST)
        ids = [ id for id in ids if self.nagiosCmds._getOb(id, None) != None]
        if not ids: return self.callZenScreen(REQUEST)
        cp = self.nagiosCmds.manage_copyObjects(ids)
        if REQUEST: 
            resp=REQUEST['RESPONSE']
            resp.setCookie('__cp', cp, path='/zport/dmd')
            REQUEST['__cp'] = cp
            return self.callZenScreen(REQUEST)
        return cp


    def manage_pasteNagiosCmds(self, cb_copy_data=None, REQUEST=None):
        """Paste NagiosCmds that have been copied before.
        """
        cp = None
        if cb_copy_data: cp = cb_copy_data
        elif REQUEST:
            cp = REQUEST.get("__cp",None)
        if cp: self.nagiosCmds.manage_pasteObjects(cp)
        if REQUEST: 
            REQUEST['RESPONSE'].setCookie('__cp', 'deleted', path='/zport/dmd',
                            expires='Wed, 31-Dec-97 23:59:59 GMT')
            REQUEST['__cp'] = None
            return self.callZenScreen(REQUEST)



InitializeClass(NagiosTemplate)
