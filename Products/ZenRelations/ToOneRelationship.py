###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__="""ToOneRelationship

ToOneRelationship is a class used on a RelationshipManager
to give it toOne management Functions.
"""

import logging
log = logging.getLogger("zen.Relations")


# Base classes for ToOneRelationship
from RelationshipBase import RelationshipBase

from Globals import InitializeClass
from Globals import DTMLFile
from AccessControl import ClassSecurityInfo
from App.Dialogs import MessageDialog
from Acquisition import aq_base

from zExceptions import NotFound
from Products.ZenRelations.Exceptions import *
from Products.ZenUtils.Utils import unused, getObjByPath

def manage_addToOneRelationship(context, id, REQUEST = None):
    """ToOneRelationship Factory"""
    r =  ToOneRelationship(id)
    context._setObject(id, r)
    if REQUEST:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')



addToOneRelationship = DTMLFile('dtml/addToOneRelationship',globals())


class ToOneRelationship(RelationshipBase):
    """ToOneRelationship represents a to one Relationship
    on a RelationshipManager"""

    meta_type = 'ToOneRelationship'

    security = ClassSecurityInfo()


    def __init__(self, id):
        self.id = id
        self.obj = None


    def __call__(self):
        """return the related object when a ToOne relation is called"""
        # Disabling relationship checking code.
        # http://dev.zenoss.org/trac/ticket/5391
        #self.checkRelation(True)
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
        self.__primary_parent__._p_changed = True


    def _remove(self,obj=None, suppress_events=False):
        """remove the to one side of a relationship"""
        if obj == None or obj == self.obj:
            self.obj = None
            self.__primary_parent__._p_changed = True
        else:
            raise ObjectNotFound( "object %s was not found on %s" % (obj, self))


    def _remoteRemove(self, obj=None):
        """clear the remote side of this relationship"""
        if self.obj:
            if obj != None and obj != self.obj:
                raise ObjectNotFound(
                        "object %s was not found on %s it has object %s" %
                        (obj.getPrimaryId(), self.getPrimaryId(),
                        self.obj.getPrimaryId()))
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


    def manage_afterAdd(self, item, container):
        """Don't do anything here because we have on containment"""
        pass


    def manage_afterClone(self, item):
        """Don't do anything here because we have on containment"""
        pass


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
    def getPrimaryLink(self, target=None):
        """get the link tag of a related object"""
        link = ""
        if self.obj:
            if not self.obj.checkRemotePerm("View", self.obj):
                link = self.obj.id
            else:
                attributes = ''
                if target is not None:
                    attributes = "target='%s' " % (target,)
                link = "<a %shref='%s'>%s</a>" % (
                    attributes,
                    self.obj.getPrimaryUrlPath(),
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
        log.debug("checking relation: %s", self.id)

        try:
            ppath = self.obj.getPrimaryPath()
            getObjByPath(self, ppath)
        except (KeyError, NotFound):
            log.error("object %s in relation %s has been deleted " \
                         "from its primary path",
                         self.obj.getPrimaryId(), self.getPrimaryId())
            if repair:
                log.warn("removing object %s from relation %s",
                         self.obj.getPrimaryId(), self.getPrimaryId())
                self.obj = None

        if not self.obj: return

        rname = self.remoteName()
        rrel = getattr(self.obj, rname)
        parobj = self.getPrimaryParent()
        if not rrel.hasobject(parobj):
            log.error("remote relation %s doesn't point back to %s",
                      rrel.getPrimaryId(), self.getPrimaryId())
            if repair:
                log.warn("reconnecting relation %s to relation %s",
                        rrel.getPrimaryId(), self.getPrimaryId())
                rrel._add(parobj)


InitializeClass(ToOneRelationship)
