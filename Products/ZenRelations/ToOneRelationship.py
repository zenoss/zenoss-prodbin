#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""ToOneRelationship

ToOneRelationship is a class used on a RelationshipManager
to give it toOne management Functions.

$Id: ToOneRelationship.py,v 1.23 2003/10/02 20:48:22 edahl Exp $"""

__version__ = "$Revision: 1.23 $"[11:-2]

import copy

import logging
log = logging.getLogger("zen.Relations")


# Base classes for ToOneRelationship
from RelationshipBase import RelationshipBase
from OFS.SimpleItem import SimpleItem

from Globals import InitializeClass
from Globals import DTMLFile
from AccessControl import ClassSecurityInfo
from App.Dialogs import MessageDialog
from Acquisition import aq_base, aq_parent

from Products.ZenRelations.Exceptions import *

def manage_addToOneRelationship(context, id, REQUEST = None):
    """ToOneRelationship Factory"""
    r =  ToOneRelationship(id)
    context._setObject(id, r)
    if REQUEST:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
                                     


addToOneRelationship = DTMLFile('dtml/addToOneRelationship',globals())


class ToOneRelationship(RelationshipBase, SimpleItem):
    """ToOneRelationship represents a to one Relationship 
    on a RelationshipManager"""

    meta_type = 'ToOneRelationship'
   
    security = ClassSecurityInfo()


    def __init__(self, id):
        self.id = id
        self.obj = None

    
    def __call__(self):
        """return the related object when a ToOne relation is called"""
        return self.obj


    def hasobject(self, obj):
        """does this relation point to the object passed"""
        return self.obj == obj


    def _add(self, obj):
        """add a to one side of a relationship
        if a relationship already exists clear it"""
        if obj == self.obj: raise RelationshipExistsError
        self._remoteRemove()
        self.obj = aq_base(obj)


    def _remove(self,obj=None):
        """remove the to one side of a relationship"""
        if obj == None or obj == self.obj:
            self.obj = None 
        else:
            raise ObjectNotFound


    def _remoteRemove(self, obj=None):
        """clear the remote side of this relationship"""
        if self.obj:
            if obj != None and obj != self.obj: raise ObjectNotFound
            remoteRel = getattr(aq_base(self.obj), self.remoteName())
            remoteRel._remove(self.__primary_parent__)


    security.declareProtected('View', 'getRelatedId')
    def getRelatedId(self):
        '''return the id of the our related object'''
        if self.obj:
            return self.obj.id
        else:
            return None

 
    def _getCopy(self, container):
        """
        Create ToOne copy. If this is the one side of one to many
        we set our side of the relation to point towards the related
        object (maintain the relationship across the copy).
        """
        rel = self.__class__(self.id)
        rel.__primary_parent__ = container
        rel = rel.__of__(container)
        if (self.remoteTypeName() == "ToMany" and self.obj):
            rel.addRelation(self.obj)
        return rel


    def manage_beforeDelete(self, item, container):
        """
        There are 4 possible states during when beforeDelete is called.
        They are defined by the attribute _operation and can be: 
            -1 = object being deleted remove relation
            0 = copy, 1 = move, 2 = rename
        Any state less than 1 will provoke deletion of the remote end of the
        relationship.
        ToOne doesn't call beforeDelete on its related object because its 
        not a container.
        """
        if getattr(item, "_operation", -1) < 1: 
            self._remoteRemove()


    def manage_workspace(self, REQUEST):
        """ZMI function to return the workspace of the related object"""
        if self.obj:
            objurl = self.obj.getPrimaryUrlPath()
            REQUEST['RESPONSE'].redirect(objurl+'/manage_workspace')
        else:
            return MessageDialog(
                title = "No Relationship Error",
                message = "This relationship does not currently point" \
                            " to an object",
                action = "manage_main")


    def manage_main(self, REQUEST=None):
        """ZMI function to redirect to parent relationship manager"""
        REQUEST['RESPONSE'].redirect(
            self.getPrimaryParent().getPrimaryUrlPath()+'/manage_workspace')

    
    #FIXME - please make me go away, I'm so ugly!
    security.declareProtected('View', 'getPrimaryLink')
    def getPrimaryLink(self):
        """get the link tag of a related object"""
        link = ""
        if self.obj:
            link = "<a href='%s'>%s</a>" % (self.obj.getPrimaryUrlPath(),
                                            self.obj.id)
        return link


    def getPrimaryHref(self):
        """Return the primary URL for our related object.
        """
        return self.obj.getPrimaryUrlPath()


    def exportXml(self,ofile,ignorerels=[]):
        """return an xml representation of a ToOneRelationship
        <toone id='cricket'>
            /Monitors/Cricket/crk0.srv.hcvlny.cv.net
        </toone>"""
        from RelSchema import ToManyCont
        if not self.obj or self.remoteType()==ToManyCont: return
        ofile.write("<toone id='%s' objid='%s'/>\n" % (
                    self.id, self.obj.getPrimaryId()))
    
    
    def checkRelation(self, repair=False):
        """Check to make sure that relationship bidirectionality is ok.
        """
        if not self.obj: return
        log.info("checking relation: %s", self.id)
        try:
            ppath = self.obj.getPrimaryPath()
            self.getObjByPath(ppath)
        except KeyError:
            log.critical("obj:%s rel:%s robj:%s no longer exists",
                    self.getPrimaryId(), self.id, self.obj.getPrimaryId())
            if repair: 
                log.warn("removing rel to:%s", self.obj.getPrimaryId())
                self.obj = None
        rname = self.remoteName()
        rrel = getattr(self.obj, rname)
        parobj = self.getPrimaryParent() 
        if not rrel.hasobject(parobj):
            log.critical("obj:%s rel:%s robj:%s rrel:%s doesn't point back",
                parobj.getPrimaryId(),self.id,self.obj.getPrimaryId(),rname)
            if repair:
                log.warn("adding obj:%s to rrel:%s", 
                        self.getPrimaryId(),rname)
                rrel._add(parobj)


InitializeClass(ToOneRelationship)
