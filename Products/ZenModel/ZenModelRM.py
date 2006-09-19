#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""ZenModelRM

$Id: ZenModelRM.py,v 1.50 2004/05/10 20:49:09 edahl Exp $"""

__version__ = "$Revision: 1.50 $"[11:-2]

import os
import time

# base classes of ZenModelRM
from ZenModelBase import ZenModelBase
from Products.ZenRelations.RelationshipManager import RelationshipManager
from OFS.History import Historical
#from Products.ZCatalog.CatalogAwareness import CatalogAware

from Acquisition import aq_base
from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from Globals import InitializeClass
from DateTime import DateTime
from ZPublisher.Converters import type_converters

from Products.ZenUtils.Utils import getSubObjects


class ZenModelRM(ZenModelBase, RelationshipManager, Historical):
    """
    Base class for all Persistent classes that have relationships.
    Provides RelationshipManagement, Customized PropertyManagement,
    Catalog Indexing, and Historical change tracking.
    """

    zenRelationsBaseModule = "Products.ZenModel"

    meta_type = 'ZenModelRM'

    default_catalog = ''

    isInTree = 0 #should this class show in left nav tree

    security = ClassSecurityInfo()
   
    def __init__(self, id, title=None, buildRelations=True):
        self.createdTime = DateTime(time.time())
        RelationshipManager.__init__(self, id, title, buildRelations)

   
    security.declareProtected('Manage DMD', 'rename')
    def rename(self, newId, REQUEST=None):
        """Delete device from the DMD"""
        renamed = False
        if newId and newId != self.getId():
            parent = self.getPrimaryParent()
            parent.manage_renameObject(self.getId(), newId)
            renamed = True
        if REQUEST:
            return self.callZenScreen(REQUEST, renamed)
        return renamed


    security.declareProtected('Manage DMD', 'zmanage_editProperties')
    def zmanage_editProperties(self, REQUEST=None):
        """Edit a ZenModel object and return its proper page template
        """
        redirect = False
        if REQUEST.form.has_key("newId"):
            redirect = self.rename(REQUEST.form["newId"])
        self.manage_changeProperties(**REQUEST.form)
        if REQUEST:
            REQUEST['message'] = "Saved at time:"
            return self.callZenScreen(REQUEST, redirect)


    def zmanage_addProperty(self, id, value, type, label, visible,REQUEST=None):
        """Add a new property via the web.
        Sets a new property with the given id, type, and value.
        """
        if type_converters.has_key(type):
            value=type_converters[type](value)
        self._setProperty(id.strip(), value, type, label, visible)
        if REQUEST:
            return self.callZenScreen(REQUEST)

    def zmanage_exportObject(self, REQUEST=None):
        """Export objects to specific locations.
        """
        redirect = False
        dest = REQUEST.form.get('dest')
        zenhome = os.getenv('ZENHOME')
        expDir = os.path.join(zenhome, 'export')
        fileBase = '%s_%s.xml' % (self.getNodeName(), self.id)
        if dest == 'filesystem':
            filename = os.path.join(expDir, fileBase)
            msg = "Item has been exported to: %s at " % filename
        elif dest == 'zenossdotnet':
            # create temp file
            filename = ''
            # get username and password from configuration
            username = ''
            password = ''
            # get https URL for user space at Zenoss.net
            url = 'https://%s:%s@zenoss.net/'
            # build XML-RPC proxy object for publishing to Zenoss.net
            server = xmlrpclib.ProxyServer(url)
            msg = "Item has been exported to: %s. Note that you will need to "
            msg += "login at Zenoss.net and publish this template in order to "
            msg += "share it with others. Exported at " % url
        # open file
        exportFile = open(filename, 'w+')
        # export object to file
        self.exportXml(exportFile)
        # cleanup
        exportFile.close()
        if dest == 'zenossdotnet':
            # get data
            exportFile = open(filename)
            dataToSend = exportFile.read()
            exportFile.close()
            # push data up to Zenoss.net
            server.postUserTemplate(dataToSend)
        if REQUEST:
            REQUEST['message'] = msg
            return self.callZenScreen(REQUEST, redirect)

    def zmanage_importObject(self, REQUEST=None):
        """Import objects into Zenoss.
        """
        pass

    def zmanage_delProperties(self, ids=(), REQUEST=None):
        """Delete properties from an object.
        """
        for id in ids:
            self._delProperty(id)
        if REQUEST:
            return self.callZenScreen(REQUEST)

   
    def zmanage_delObjects(self, ids=(), relation="", REQUEST=None):
        """Delete objects from this object or one of its relations.
        """
        target = self
        if relation: target = self._getOb(relation)
        for id in ids:
            target._delObject(id)
        if REQUEST:
            return self.callZenScreen(REQUEST)
        

    security.declareProtected('View', 'getDmdKey')
    def getDmdKey(self):
        return self.getId()
    
        
    security.declareProtected('View', 'primarySortKey')
    def primarySortKey(self):
        return self.getId()
    
        
    security.declareProtected('View', 'viewName')
    def viewName(self):
        return self.getId()
    
        
    #actions?
    def getTreeItems(self):
        nodes = []
        for item in self.objectValues():
            if hasattr(aq_base(item), "isInTree") and item.isInTree:
                nodes.append(item)
        return nodes
  

    def getSubObjects(self, filter=None, decend=None, retobjs=None):
        return getSubObjects(self, filter, decend, retobjs)


    def getCreatedTimeString(self):
        """return the creation time as a string"""
        return self.createdTime.strftime('%Y/%m/%d %H:%M:%S')


    def getModificationTimeString(self):
        """return the modification time as a string"""
        return self.bobobase_modification_time().strftime('%Y/%m/%d %H:%M:%S')


    def changePythonClass(self, newPythonClass, container):
        """change the python class of a persistent object"""
        id = self.id
        nobj = newPythonClass(id) #make new instance from new class
        nobj = nobj.__of__(container) #make aq_chain same as self
        nobj.oldid = self.id
        nobj.setPrimaryPath() #set up the primarypath for the copy
        #move all sub objects to new object
        nrelations = self.ZenSchemaManager.getRelations(nobj).keys()
        for sobj in self.objectValues():
            RelationshipManager._delObject(self,sobj.getId())
            if not hasattr(nobj, sobj.id) and sobj.id in nrelations:
                RelationshipManager._setObject(nobj, sobj.id, sobj)
        nobj.buildRelations() #build out any missing relations
        # copy properties to new object
        noprop = getattr(nobj, 'zNoPropertiesCopy', [])
        for name in nobj.getPropertyNames():
            if (getattr(self, name, None) and name not in noprop and
                hasattr(nobj, "_updateProperty")):
                val = getattr(self, name)
                nobj._updateProperty(name, val)
        return aq_base(nobj)

    
    def getZenRootNode(self):
        """Return the root node for our zProperties."""
        return self.getDmdRoot(self.dmdRootName)

    
    def editableDeviceList(self):
        """
        Return true if user has Manager role and self has a deviceList.
        """
        user = self.REQUEST.get('AUTHENTICATED_USER', None)
        if user: 
            return "Manager" in user.getRoles() and \
                getattr(aq_base(self), "deviceMoveTargets", False)


    def creator(self):
        """
        Method needed for CatalogAwarnessInterface.  Implemented here so that
        Subclasses (who would have the same implementation) don't need to.
        Other methods (except reindex_all) are implemented on the concreate
        class.
        """
        users=[]
        for user, roles in self.get_local_roles():
            if 'Owner' in roles:
                users.append(user)
        return ', '.join(users)


    def reindex_all(self, obj=None):
        """
        Called for in the CataLogAwarenessInterface not sure this is needed.
        """
        if obj is None: obj=self
        if hasattr(aq_base(obj), 'index_object'):
            obj.index_object()
        if hasattr(aq_base(obj), 'objectValues'):
            sub=obj.objectValues()
            for item in sub:
                self.reindex_all(item)
        return 'done!'
