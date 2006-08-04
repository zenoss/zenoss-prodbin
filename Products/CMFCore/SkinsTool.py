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
"""Portal skins tool.

$Id: SkinsTool.py 36910 2005-04-07 16:37:47Z yuppie $
"""

from AccessControl import ClassSecurityInfo
from Acquisition import aq_base
from DateTime import DateTime
from Globals import DTMLFile
from Globals import InitializeClass
from Globals import PersistentMapping
from OFS.DTMLMethod import DTMLMethod
from OFS.Folder import Folder
from OFS.Image import Image
from OFS.ObjectManager import REPLACEABLE
from Products.PageTemplates.ZopePageTemplate import ZopePageTemplate
from Products.PythonScripts.PythonScript import PythonScript

from ActionProviderBase import ActionProviderBase
from DirectoryView import base_ignore
from DirectoryView import ignore
from DirectoryView import ignore_re
from interfaces.portal_skins import portal_skins as ISkinsTool
from permissions import AccessContentsInformation
from permissions import ManagePortal
from permissions import View
from SkinsContainer import SkinsContainer
from utils import _dtmldir
from utils import getToolByName
from utils import UniqueObject


def modifiedOptions():
    # Remove the existing "Properties" option and add our own.
    rval = []
    pos = -1
    for o in Folder.manage_options:
        label = o.get('label', None)
        if label != 'Properties':
            rval.append(o)
    rval[1:1] = [{'label':'Properties',
                  'action':'manage_propertiesForm'}]
    return tuple(rval)


class SkinsTool(UniqueObject, SkinsContainer, Folder, ActionProviderBase):
    """ This tool is used to supply skins to a portal.
    """

    __implements__ = (ISkinsTool, SkinsContainer.__implements__,
                      ActionProviderBase.__implements__)

    id = 'portal_skins'
    meta_type = 'CMF Skins Tool'
    _actions = ()

    allow_any = 0
    cookie_persistence = 0
    default_skin = ''
    request_varname = 'portal_skin'
    selections = None

    security = ClassSecurityInfo()

    manage_options = ( modifiedOptions() +
                      ({ 'label' : 'Overview', 'action' : 'manage_overview' }
                     ,
                     ) + ActionProviderBase.manage_options
                     )

    def __init__(self):
        self.selections = PersistentMapping()

    def _getSelections(self):
        sels = self.selections
        if sels is None:
            # Backward compatibility.
            self.selections = sels = PersistentMapping()
        return sels

    #
    #   ZMI methods
    #
    security.declareProtected(ManagePortal, 'manage_overview')
    manage_overview = DTMLFile( 'explainSkinsTool', _dtmldir )

    security.declareProtected(ManagePortal, 'manage_propertiesForm')
    manage_propertiesForm = DTMLFile('dtml/skinProps', globals())

    # the following two methods override those in FindSupport, to
    # support marking of objects used in specific skins
    security.declareProtected(ManagePortal, 'manage_findResult')
    manage_findResult = DTMLFile('findResult', _dtmldir,
                                 management_view='Find')

    security.declareProtected(ManagePortal, 'manage_findForm')
    manage_findForm = DTMLFile('findForm', _dtmldir,
                               management_view='Find')



    security.declareProtected(ManagePortal, 'manage_skinLayers')
    def manage_skinLayers(self, chosen=(), add_skin=0, del_skin=0,
                          skinname='', skinpath='', REQUEST=None):
        """ Change the skinLayers.
        """
        sels = self._getSelections()
        if del_skin:
            for name in chosen:
                del sels[name]

        if REQUEST is not None:
            for key in sels.keys():
                fname = 'skinpath_%s' % key
                val = REQUEST[fname]

                # if val is a list from the new lines field
                # then munge it back into a comma delimited list
                # for hysterical reasons
                if isinstance(val, list):
                    val = ','.join([layer.strip() for layer in val])

                if sels[key] != val:
                    self.testSkinPath(val)
                    sels[key] = val

        if add_skin:
            skinpath = ','.join([layer.strip() for layer in skinpath])
            self.testSkinPath(skinpath)
            sels[str(skinname)] = skinpath

        if REQUEST is not None:
            return self.manage_propertiesForm(
                self, REQUEST, management_view='Properties', manage_tabs_message='Skins changed.')


    security.declareProtected(ManagePortal, 'isFirstInSkin')
    def isFirstInSkin(self, template_path, skin=None):
        """
        Is the specified template the one that would get returned from the current
        skin?
        """
        if skin is None or skin == 'None':
            skin = self.getDefaultSkin()
        template = self.restrictedTraverse(template_path)
        name = template.getId()
        skin_path = self.getSkinPath(skin)
        if not skin_path:
            return 0
        parts = list(skin_path.split(","))
        found = ""
        for part in parts:
            part = part.strip()
            if part[0] == "_":
                continue
            partob = getattr(self, part, None)
            if partob:
                skin_template = getattr(partob.aq_base, name, None)
                if skin_template:
                    found = skin_template
                    break
        if found == template:
            return 1
        else:
            return 0

    security.declareProtected(ManagePortal, 'manage_properties')
    def manage_properties(self, default_skin='', request_varname='',
                          allow_any=0, chosen=(), add_skin=0,
                          del_skin=0, skinname='', skinpath='',
                          cookie_persistence=0, REQUEST=None):
        """ Changes portal_skin properties. """
        self.default_skin = str(default_skin)
        self.request_varname = str(request_varname)
        self.allow_any = allow_any and 1 or 0
        self.cookie_persistence = cookie_persistence and 1 or 0
        if REQUEST is not None:
            return self.manage_propertiesForm(
                self, REQUEST, management_view='Properties', manage_tabs_message='Properties changed.')

    security.declarePrivate('PUT_factory')

    def PUT_factory( self, name, typ, body ):
        """
            Dispatcher for PUT requests to non-existent IDs.  Returns
            an object of the appropriate type (or None, if we don't
            know what to do).
        """
        major, minor = typ.split('/', 1)

        if major == 'image':
            return Image( id=name
                        , title=''
                        , file=''
                        , content_type=typ
                        )

        if major == 'text':

            if minor == 'x-python':
                return PythonScript( id=name )

            if minor in ('html', 'xml'):
                return ZopePageTemplate( name )

            return DTMLMethod( __name__=name )

        return None

    # Make the PUT_factory replaceable
    PUT_factory__replaceable__ = REPLACEABLE


    security.declarePrivate('testSkinPath')
    def testSkinPath(self, p):
        """ Calls SkinsContainer.getSkinByPath().
        """
        self.getSkinByPath(p, raise_exc=1)

    #
    #   'SkinsContainer' interface methods
    #
    security.declareProtected(AccessContentsInformation, 'getSkinPath')
    def getSkinPath(self, name):
        """ Convert a skin name to a skin path.
        """
        sels = self._getSelections()
        p = sels.get(name, None)
        if p is None:
            if self.allow_any:
                return name
        return p  # Can be None

    security.declareProtected(AccessContentsInformation, 'getDefaultSkin')
    def getDefaultSkin(self):
        """ Get the default skin name.
        """
        return self.default_skin

    security.declareProtected(AccessContentsInformation, 'getRequestVarname')
    def getRequestVarname(self):
        """ Get the variable name to look for in the REQUEST.
        """
        return self.request_varname

    #
    #   UI methods
    #
    security.declareProtected(AccessContentsInformation, 'getAllowAny')
    def getAllowAny(self):
        '''
        Used by the management UI.  Returns a flag indicating whether
        users are allowed to use arbitrary skin paths.
        '''
        return self.allow_any

    security.declareProtected(AccessContentsInformation, 'getCookiePersistence')
    def getCookiePersistence(self):
        '''
        Used by the management UI.  Returns a flag indicating whether
        the skins cookie is persistent or not.
        '''
        return self.cookie_persistence

    security.declareProtected(AccessContentsInformation, 'getSkinPaths')
    def getSkinPaths(self):
        '''
        Used by the management UI.  Returns the list of skin name to
        skin path mappings as a sorted list of tuples.
        '''
        sels = self._getSelections()
        rval = []
        for key, value in sels.items():
            rval.append((key, value))
        rval.sort()
        return rval

    #
    #   'portal_skins' interface methods
    #
    security.declarePublic('getSkinSelections')
    def getSkinSelections(self):
        """ Get the sorted list of available skin names.
        """
        sels = self._getSelections()
        rval = list(sels.keys())
        rval.sort()
        return rval

    security.declareProtected(View, 'updateSkinCookie')
    def updateSkinCookie(self):
        """ If needed, updates the skin cookie based on the member preference.
        """
        mtool = getToolByName(self, 'portal_membership')
        utool = getToolByName(self, 'portal_url')
        member = mtool.getAuthenticatedMember()
        if hasattr(aq_base(member), 'portal_skin'):
            mskin = member.portal_skin
            if mskin:
                req = self.REQUEST
                cookie = req.cookies.get(self.request_varname, None)
                if cookie != mskin:
                    resp = req.RESPONSE
                    portal_path = req['BASEPATH1'] + '/' + utool(1)

                    if not self.cookie_persistence:
                        # *Don't* make the cookie persistent!
                        resp.setCookie(self.request_varname, mskin,
                                       path=portal_path)
                    else:
                        expires = ( DateTime( 'GMT' ) + 365 ).rfc822()
                        resp.setCookie( self.request_varname
                                      , mskin
                                      , path=portal_path
                                      , expires=expires
                                      )
                    # Ensure updateSkinCookie() doesn't try again
                    # within this request.
                    req.cookies[self.request_varname] = mskin
                    req[self.request_varname] = mskin
                    return 1
        return 0

    security.declareProtected(View, 'clearSkinCookie')
    def clearSkinCookie(self):
        """ Expire the skin cookie.
        """
        req = self.REQUEST
        resp = req.RESPONSE
        utool = getToolByName(self, 'portal_url')
        portal_path = req['BASEPATH1'] + '/' + utool(1)
        resp.expireCookie(self.request_varname, path=portal_path)

    security.declareProtected(ManagePortal, 'addSkinSelection')
    def addSkinSelection(self, skinname, skinpath, test=0, make_default=0):
        '''
        Adds a skin selection.
        '''
        sels = self._getSelections()
        skinpath = str(skinpath)

        # Basic precaution to make sure the stuff we want to ignore in
        # DirectoryViews gets prevented from ending up in a skin path
        path_elems = [x.strip() for x in skinpath.split(',')]
        ignored = base_ignore + ignore

        for elem in path_elems[:]:
            if elem in ignored or ignore_re.match(elem):
                path_elems.remove(elem)

        skinpath = ','.join(path_elems)

        if test:
            self.testSkinPath(skinpath)
        sels[str(skinname)] = skinpath
        if make_default:
            self.default_skin = skinname

InitializeClass(SkinsTool)
