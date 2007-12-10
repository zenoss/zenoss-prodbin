##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights
# Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this
# distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" DomainAuthHelper   Authentication Plugin for Domain authentication
"""

__doc__     = """ Authentication Plugin for Domain authentication """
__version__ = '$Revision: 69827 $'[11:-2]

# General Python imports
import socket, os, time, copy, re

# General Zope imports
from BTrees.OOBTree import OOBTree
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import manage_users
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

# PluggableAuthService imports
from Products.PluggableAuthService.interfaces.plugins import \
    IAuthenticationPlugin
from Products.PluggableAuthService.interfaces.plugins import \
    IExtractionPlugin
from Products.PluggableAuthService.interfaces.plugins import \
    IRolesPlugin
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements
from Products.PluggableAuthService.utils import Interface

class IDomainAuthHelper(Interface):
    """ Marker interface.
    """

_MATCH_EQUALS = 'equals'
_MATCH_ENDSWITH = 'endswith'
_MATCH_REGEX = 'regex'

manage_addDomainAuthHelperForm = PageTemplateFile(
    'www/daAdd', globals(), __name__='manage_addDomainAuthHelperForm' )

def manage_addDomainAuthHelper(self, id, title='', REQUEST=None):
    """ Factory method to instantiate a DomainAuthHelper """
    obj = DomainAuthHelper(id, title=title)
    self._setObject(id, obj)

    if REQUEST is not None:
        qs = 'manage_tabs_message=DomainAuthHelper+added.'
        my_url = self.absolute_url()
        REQUEST['RESPONSE'].redirect('%s/manage_workspace?%s' % (my_url, qs))


class DomainAuthHelper(BasePlugin):
    """ Domain Authentication plugin for the PluggableAuthService """
    security = ClassSecurityInfo()
    meta_type = 'Domain Authentication Plugin'

    security.declareProtected(manage_users, 'manage_map')
    manage_map = PageTemplateFile('www/daMatches', globals())

    security.declareProtected(manage_users, 'manage_genericmap')
    manage_genericmap = PageTemplateFile('www/daGeneric', globals())

    manage_options = ( BasePlugin.manage_options[:1]
                     + ( { 'label'  : 'User Map'
                         , 'action' : 'manage_map'
                       # , 'help'   : ( 'PluggableAuthService'
                       #              ,'matches.stx')
                         }
                       , { 'label'  : 'Generic Map'
                         , 'action' : 'manage_genericmap'
                         }
                       )
                     + BasePlugin.manage_options[1:]
                     )


    def __init__(self, id, title=''):
        """ Initialize a new instance """
        self.id = id
        self.title = title
        self._domain_map = OOBTree()


    security.declarePrivate('extractCredentials')
    def extractCredentials(self, request):
        """ Extract credentials from 'request'.
        """
        creds = {}

        remote_host = request.get('REMOTE_HOST', '')
        if remote_host:
            creds['remote_host'] = request.get('REMOTE_HOST', '')

            try:
                creds['remote_address'] = request.getClientAddr()
            except AttributeError:
                creds['remote_address'] = request.get('REMOTE_ADDR', '')

        return creds

    security.declarePrivate('authenticateCredentials')
    def authenticateCredentials(self, credentials):
        """ Fulfill AuthenticationPlugin requirements """
        login = credentials.get('login', '')
        r_host = credentials.get('remote_host', '')
        r_address = credentials.get('remote_address', '')
        matches = self._findMatches(login, r_host, r_address)

        if len(matches) > 0:
            if login:
                return (login, login)
            else:
                best_match = matches[0]
                u_name = best_match.get('username', 'remote')
                return ( best_match.get('user_id', u_name)
                       , u_name
                       )

        return (None, None)


    security.declarePrivate( 'getRolesForPrincipal' )
    def getRolesForPrincipal(self, user, request=None):
        """ Fulfill RolesPlugin requirements """
        roles = []

        if request is None:
            # Without request there is no way I can do anything...
            return tuple(roles)

        uname = user.getUserName()

        if uname.find('Remote User') != -1:
            uname = ''

        matches = self._findMatches( uname
                                   , request.get('REMOTE_HOST', '')
                                   , request.getClientAddr()
                                   )

        # We want to grab the first match because it is the most specific
        if len(matches) > 0:
            roles = matches[0].get('roles', [])

        return tuple(roles)


    security.declarePrivate('_findMatches')
    def _findMatches(self, login, r_host='', r_address=''):
        """ Find the match """
        matches = []

        if not r_host and not r_address:
            return tuple(matches)
        
        all_info = list(self._domain_map.get(login, []))
        all_info.extend(self._domain_map.get(''))
        
        if not r_host:
            try:
                r_host = socket.gethostbyaddr(r_address)[0]
            except socket.herror: 
                pass

        if not r_address:
            try:
                r_address = socket.gethostbyname(r_host)
            except socket.herror :
                pass

        if not r_host and not r_address:
            return tuple(matches)

        candidates = [r_host, r_address]

        for match_info in all_info:
            m = []
            m_type = match_info['match_type']
            m_real = match_info['match_real']

            if m_type == _MATCH_EQUALS:
                m = [match_info for x in candidates if x == m_real]
            elif m_type == _MATCH_ENDSWITH:
                m = [match_info for x in candidates if x.endswith(m_real)]
            elif m_type == _MATCH_REGEX:
                m = [match_info for x in candidates if m_real.search(x)]

            matches.extend(m)

        return tuple(matches)


    security.declareProtected(manage_users, 'listMatchTypes')
    def listMatchTypes(self):
        """ Return a sequence of possible match types """
        return (_MATCH_EQUALS, _MATCH_ENDSWITH, _MATCH_REGEX)


    security.declareProtected(manage_users, 'listMappingsForUser')
    def listMappingsForUser(self, user_id=''):
        """ List the mappings for a specific user """
        result = []
        record = self._domain_map.get(user_id, [])

        for match_info in record:
            result.append( { 'match_type' : match_info['match_type']
                           , 'match_string' : match_info['match_string']
                           , 'match_id' : match_info['match_id']
                           , 'roles' : match_info['roles']
                           , 'username' : match_info['username']
                           } )
        
        return result


    security.declareProtected(manage_users, 'manage_addMapping')
    def manage_addMapping( self
                         , user_id=''
                         , match_type=''
                         , match_string=''
                         , username=''
                         , roles=[]
                         , REQUEST=None
                         ):
        """ Add a mapping for a user """
        msg = ''

        if match_type not in (_MATCH_EQUALS, _MATCH_ENDSWITH, _MATCH_REGEX):
            msg = 'Unknown match type %s' % match_type

        if not match_string:
            msg = 'No match string specified'

        if match_type == _MATCH_REGEX:
            try:
                re.compile(match_string, re.IGNORECASE)
            except re.error:
                msg = 'Invalid regular expression %s' % match_string

        if msg:
            if REQUEST is not None:
                return self.manage_map(manage_tabs_message=msg)

            raise ValueError, msg

        record = self._domain_map.get(user_id, [])
        if match_type == _MATCH_REGEX:
            real_match = re.compile(match_string, re.IGNORECASE)
        else:
            real_match = match_string

        match = { 'match_type' : match_type
                , 'match_string' : match_string
                , 'match_real' : real_match
                , 'match_id' : '%s_%s' % (user_id, str(time.time()))
                , 'username' : user_id or username or 'Remote User'
                , 'roles' : roles
                }

        if match not in record:
            record.append(match)
        else:
            msg = 'Match already exists'

        self._domain_map[user_id] = record

        if REQUEST is not None:
            msg = msg or 'Match added.'
            if user_id:
                return self.manage_map(manage_tabs_message=msg)
            else:
                return self.manage_genericmap(manage_tabs_message=msg)


    security.declareProtected(manage_users, 'manage_removeMappings')
    def manage_removeMappings(self, user_id='', match_ids=[], REQUEST=None):
        """ Remove mappings """
        msg = ''

        if len(match_ids) < 1:
            msg = 'No matches specified'

        record = self._domain_map.get(user_id, [])

        if len(record) < 1:
            msg = 'No mappings for user %s' % user_id

        if msg:
            if REQUEST is not None:
                return self.manage_map(manage_tabs_message=msg)
            else:
                return

        to_delete = [x for x in record if x['match_id'] in match_ids]

        for match in to_delete:
            record.remove(match)

        self._domain_map[user_id] = record

        if REQUEST is not None:
            msg = 'Matches deleted'
            if user_id:
                return self.manage_map(manage_tabs_message=msg)
            else:
                return self.manage_genericmap(manage_tabs_message=msg)

classImplements( DomainAuthHelper
               , IDomainAuthHelper
               , IExtractionPlugin
               , IAuthenticationPlugin
               , IRolesPlugin
               )

InitializeClass(DomainAuthHelper)

