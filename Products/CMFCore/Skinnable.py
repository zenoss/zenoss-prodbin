##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" Base class for object managers which can be "skinned".

Skinnable object managers inherit attributes from a skin specified in
the browser request.  Skins are stored in a fixed-name subobject.

$Id: Skinnable.py 39938 2005-11-05 21:39:56Z tseaver $
"""

from thread import get_ident
from AccessControl import ClassSecurityInfo
from Acquisition import aq_base
from Acquisition import ImplicitAcquisitionWrapper
from Globals import InitializeClass
from OFS.ObjectManager import ObjectManager
from ZODB.POSException import ConflictError


# superGetAttr is assigned to whatever ObjectManager.__getattr__
# used to do.
try:
    superGetAttr = ObjectManager.__getattr__
except AttributeError:
    try:
        superGetAttr = ObjectManager.inheritedAttribute('__getattr__')
    except AttributeError:
        superGetAttr = None

_marker = []  # Create a new marker object.


SKINDATA = {} # mapping thread-id -> (skinobj, skinname, ignore, resolve)

class SkinDataCleanup:
    """Cleanup at the end of the request."""
    def __init__(self, tid):
        self.tid = tid
    def __del__(self):
        tid = self.tid
        if SKINDATA.has_key(tid):
            del SKINDATA[tid]


class SkinnableObjectManager(ObjectManager):

    security = ClassSecurityInfo()

    security.declarePrivate('getSkinsFolderName')
    def getSkinsFolderName(self):
        # Not implemented.
        return None

    def __getattr__(self, name):
        '''
        Looks for the name in an object with wrappers that only reach
        up to the root skins folder.

        This should be fast, flexible, and predictable.
        '''
        if not name.startswith('_') and not name.startswith('aq_'):
            sd = SKINDATA.get(get_ident())
            if sd is not None:
                ob, skinname, ignore, resolve = sd
                if not ignore.has_key(name):
                    if resolve.has_key(name):
                        return resolve[name]
                    subob = getattr(ob, name, _marker)
                    if subob is not _marker:
                        # Return it in context of self, forgetting
                        # its location and acting as if it were located
                        # in self.
                        retval = aq_base(subob)
                        resolve[name] = retval
                        return retval
                    else:
                        ignore[name] = 1
        if superGetAttr is None:
            raise AttributeError, name
        return superGetAttr(self, name)

    security.declarePrivate('getSkin')
    def getSkin(self, name=None):
        """Returns the requested skin.
        """
        skinob = None
        sfn = self.getSkinsFolderName()

        if sfn is not None:
            sf = getattr(self, sfn, None)
            if sf is not None:
               if name is not None:
                   skinob = sf.getSkinByName(name)
               if skinob is None:
                   skinob = sf.getSkinByName(sf.getDefaultSkin())
                   if skinob is None:
                       skinob = sf.getSkinByPath('')
        return skinob

    security.declarePublic('getSkinNameFromRequest')
    def getSkinNameFromRequest(self, REQUEST=None):
        '''Returns the skin name from the Request.'''
        sfn = self.getSkinsFolderName()
        if sfn is not None:
            sf = getattr(self, sfn, None)
            if sf is not None:
                return REQUEST.get(sf.getRequestVarname(), None)

    security.declarePublic('changeSkin')
    def changeSkin(self, skinname):
        '''Change the current skin.

        Can be called manually, allowing the user to change
        skins in the middle of a request.
        '''
        skinobj = self.getSkin(skinname)
        if skinobj is not None:
            tid = get_ident()
            SKINDATA[tid] = (skinobj, skinname, {}, {})
            REQUEST = getattr(self, 'REQUEST', None)
            if REQUEST is not None:
                REQUEST._hold(SkinDataCleanup(tid))

    security.declarePublic('getCurrentSkinName')
    def getCurrentSkinName(self):
        '''Return the current skin name.
        '''
        sd = SKINDATA.get(get_ident())
        if sd is not None:
            ob, skinname, ignore, resolve = sd
            if skinname is not None:
                return skinname
        # nothing here, so assume the default skin
        sfn = self.getSkinsFolderName()
        if sfn is not None:
            sf = getattr(self, sfn, None)
            if sf is not None:
                return sf.getDefaultSkin()
        # and if that fails...
        return None

    security.declarePublic('clearCurrentSkin')
    def clearCurrentSkin(self):
        """Clear the current skin."""
        tid = get_ident()
        if SKINDATA.has_key(tid):
            del SKINDATA[tid]

    security.declarePublic('setupCurrentSkin')
    def setupCurrentSkin(self, REQUEST=None):
        '''
        Sets up skindata so that __getattr__ can find it.

        Can NOT be called manually to change skins in the middle of a
        request! Use changeSkin for that.
        '''
        if REQUEST is None:
            REQUEST = getattr(self, 'REQUEST', None)
        if REQUEST is None:
            # self is not fully wrapped at the moment.  Don't
            # change anything.
            return
        if SKINDATA.has_key(get_ident()):
            # Already set up for this request.
            return
        skinname = self.getSkinNameFromRequest(REQUEST)
        self.changeSkin(skinname)

    def __of__(self, parent):
        '''
        Sneakily sets up the portal skin then returns the wrapper
        that Acquisition.Implicit.__of__() would return.
        '''
        w_self = ImplicitAcquisitionWrapper(self, parent)
        try:
            w_self.setupCurrentSkin()
        except ConflictError:
            raise
        except:
            # This shouldn't happen, even if the requested skin
            # does not exist.
            import sys
            from zLOG import LOG, ERROR
            LOG('CMFCore', ERROR, 'Unable to setupCurrentSkin()',
                error=sys.exc_info())
        return w_self

    def _checkId(self, id, allow_dup=0):
        '''
        Override of ObjectManager._checkId().

        Allows the user to create objects with IDs that match the ID of
        a skin object.
        '''
        superCheckId = SkinnableObjectManager.inheritedAttribute('_checkId')
        if not allow_dup:
            # Temporarily disable skindata.
            # Note that this depends heavily on Zope's current thread
            # behavior.
            tid = get_ident()
            sd = SKINDATA.get(tid)
            if sd is not None:
                del SKINDATA[tid]
            try:
                base = getattr(self,  'aq_base', self)
                if not hasattr(base, id):
                    # Cause _checkId to not check for duplication.
                    return superCheckId(self, id, allow_dup=1)
            finally:
                if sd is not None:
                    SKINDATA[tid] = sd
        return superCheckId(self, id, allow_dup)

InitializeClass(SkinnableObjectManager)
